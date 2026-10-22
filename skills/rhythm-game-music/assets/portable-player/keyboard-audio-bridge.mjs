import http from 'node:http';
import dgram from 'node:dgram';
import {randomBytes} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {parseArgs} from 'node:util';

export function parseAudio(packet){
  if(packet.length<32||packet.toString('ascii',0,4)!=='EIAU'||packet[4]!==2||packet[5]!==32||packet[6]!==1||packet[7]!==1)return null;
  const frames=packet.readUInt16LE(28),bytes=packet.readUInt16LE(30),rate=packet.readUInt32LE(20);
  if(rate!==16000||!frames||frames>960||bytes!==frames*2||packet.length!==32+bytes)return null;
  return {session:packet.readBigUInt64LE(8),sequence:packet.readUInt32LE(16),frames,rate,pcm:Buffer.from(packet.subarray(32))};
}
export function control(action,session,sequence){
  const p=Buffer.alloc(36);p.write('EICC');p[4]=1;p[5]=action;p.writeBigUInt64LE(session,8);p.writeUInt32LE(sequence>>>0,16);return p;
}
export function assemble(chunks,start,frames,packetFrames){
  const result=Buffer.alloc(frames*2);let copied=0;
  while(copied<frames){const position=start+copied,index=Math.floor(position/packetFrames),offset=position%packetFrames,count=Math.min(frames-copied,packetFrames-offset),data=chunks.get(index);
    if(!data)throw Error('键盘音频有丢包，本次录音未保存，请靠近路由器后重试。');
    data.copy(result,copied*2,offset*2,(offset+count)*2);copied+=count;
  }
  return result;
}
export function wav(pcm,rate=16000){
  const h=Buffer.alloc(44);h.write('RIFF');h.writeUInt32LE(36+pcm.length,4);h.write('WAVEfmt ',8);h.writeUInt32LE(16,16);h.writeUInt16LE(1,20);h.writeUInt16LE(1,22);h.writeUInt32LE(rate,24);h.writeUInt32LE(rate*2,28);h.writeUInt16LE(2,32);h.writeUInt16LE(16,34);h.write('data',36);h.writeUInt32LE(pcm.length,40);return Buffer.concat([h,pcm]);
}
export function startBridge({httpPort=4190,udpPort=17433,pageOrigin='http://127.0.0.1:4192'}={}){
  const allowed=new URL(pageOrigin);
  if(allowed.protocol!=='http:'||!['127.0.0.1','localhost'].includes(allowed.hostname)||allowed.origin!==pageOrigin)throw Error('pageOrigin必须是本机演奏页的HTTP origin，例如 http://127.0.0.1:4192');
  const udp=dgram.createSocket('udp4'),token=randomBytes(24).toString('hex');let peer=null,heartbeat=0,ready=false,session=null,sequence=0;
  const stats={};
  const clock=()=>performance.now()/1000;
  const send=(action,s)=>{if(peer)udp.send(control(action,s.id,++sequence),peer.port,peer.address);};
  function stop(s=session){if(!s)return;clearInterval(s.keepalive);send(2,s);s.cancelled=true;if(session===s)session=null;}
  udp.on('message',(p,remote)=>{
    const shape=[p.toString('ascii',0,4),p.length,p[4],p[5],p[6],p[7]].join('/');stats[shape]=(stats[shape]??0)+1;
    if(p.length>=20&&p.toString('ascii',0,4)==='EIHB'&&p[4]===1){
      if(peer&&(peer.address!==remote.address||peer.port!==remote.port)&&(session||clock()-heartbeat<10))return;
      peer={address:remote.address,port:remote.port};heartbeat=clock();ready=!!(p[5]&2);return;
    }
    if(!session||!peer||remote.address!==peer.address)return;
    if(p.length===20&&p.toString('ascii',0,4)==='EICA'&&p[4]===1&&p.readBigUInt64LE(8)===session.id){if(p[5]===1){if(p[6]!==0)session.error='键盘拒绝录音，请检查设备音频是否可用。';else session.acked=true;}return;}
    const a=parseAudio(p);if(!a||a.session!==session.id)return;
    if(session.baseSequence===undefined){session.baseSequence=a.sequence;session.packetFrames=a.frames;session.baseTime=clock()-a.frames/a.rate;}
    if(a.frames!==session.packetFrames){session.error='键盘音频分包格式发生变化，请重试。';return;}
    const index=(a.sequence-session.baseSequence)>>>0;if(index>10000){session.error='键盘音频序号不连续，请重试。';return;}
    let sum=0;for(let i=0;i<a.pcm.length;i+=2){const value=a.pcm.readInt16LE(i)/32768;sum+=value*value;}session.level=Math.min(1,Math.sqrt(sum/a.frames)*5);
    session.chunks.set(index,a.pcm);session.maxIndex=Math.max(session.maxIndex,index);session.lastAudio=clock();
  });
  const wait=async(s,predicate,timeout)=>{const until=clock()+timeout;while(!predicate()){if(s.error)throw Error(s.error);if(s.cancelled)throw Error('录音已取消');if(clock()>until)throw Error('未收到完整键盘音频，请检查键盘Wi-Fi与接收地址。');await new Promise(r=>setTimeout(r,20));}};
  const server=http.createServer(async(req,res)=>{
    const origin=req.headers.origin;
    if(!['127.0.0.1:'+(server.address()?.port??httpPort),'localhost:'+(server.address()?.port??httpPort)].includes(req.headers.host)||origin&&origin!==pageOrigin){res.writeHead(403);res.end();return;}
    if(origin){res.setHeader('Access-Control-Allow-Origin',origin);res.setHeader('Vary','Origin');}
    res.setHeader('Cache-Control','no-store');res.setHeader('Access-Control-Allow-Headers','Content-Type,X-Keyboard-Token');res.setHeader('Access-Control-Allow-Methods','GET,POST,OPTIONS');
    if(req.method==='OPTIONS'){res.writeHead(204);res.end();return;}
    const json=(status,value)=>{res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(value));};
    if(req.url==='/status'&&req.method==='GET'){json(200,{connected:!!peer&&clock()-heartbeat<6,ready:ready&&clock()-heartbeat<6,busy:!!session,level:session?.level??0,token,stats});return;}
    if(req.method!=='POST'||req.headers['x-keyboard-token']!==token){json(403,{error:'本地录音授权无效，请刷新连接状态。'});return;}
    let s;
    try{
      let raw='';for await(const part of req){raw+=part;if(raw.length>2048)throw Error('请求过长');}const body=JSON.parse(raw||'{}');
      if(req.url==='/cancel'){if(session&&body.lease===session.lease)stop();json(200,{ok:true});return;}
      if(req.url==='/prepare'){
        if(session)throw Error('键盘麦克风正在使用，请先取消当前录音。');
        if(!peer||clock()-heartbeat>=6||!ready)throw Error('未检测到键盘音频心跳，请同步键盘网络设置。');
        s={lease:randomBytes(16).toString('hex'),id:randomBytes(8).readBigUInt64LE(),chunks:new Map(),maxIndex:-1};if(!s.id)s.id=1n;session=s;
        res.on('close',()=>{if(!res.writableEnded)stop(s);});
        send(1,s);s.keepalive=setInterval(()=>send(3,s),800);
        await wait(s,()=>s.acked&&s.chunks.size>0,5);json(200,{ready:true,sampleRate:16000,lease:s.lease});return;
      }
      if(req.url==='/capture'){
        const active=session;if(!active||!active.acked||!active.chunks.size)throw Error('请先连接键盘麦克风。');
        if(body.lease!==active.lease)throw Error('录音会话已过期，请重试。');s=active;
        if(s.capturing)throw Error('当前键盘录音尚未完成。');
        const frames=Number(body.frames),delay=Number(body.delay);
        if(!Number.isInteger(frames)||frames<800||frames>16000*120||!Number.isFinite(delay)||delay<0||delay>10)throw Error('录音长度或倒数无效。');
        s.capturing=true;const start=Math.max(0,Math.round((clock()+delay-s.baseTime)*16000)),last=Math.floor((start+frames-1)/s.packetFrames);
        res.on('close',()=>{if(!res.writableEnded)stop(s);});
        await wait(s,()=>s.maxIndex>=last,delay+frames/16000+3);
        // Give reordered packets a small delivery window; never silently replace lost audio with zeros.
        await new Promise(r=>setTimeout(r,80));if(s.cancelled)throw Error('录音已取消');
        const data=wav(assemble(s.chunks,start,frames,s.packetFrames));stop(s);res.writeHead(200,{'Content-Type':'audio/wav','Content-Length':data.length});res.end(data);return;
      }
      json(404,{error:'未知录音操作'});
    }catch(e){if(s)stop(s);if(!res.destroyed)json(400,{error:e.message});}
  });
  udp.bind(udpPort,'0.0.0.0');server.listen(httpPort,'127.0.0.1');
  udp.on('error',()=>console.error('键盘音频端口不可用，请检查是否被占用。'));server.on('error',()=>console.error('本地录音接口端口不可用。'));
  const cleanup=setInterval(()=>{if(session&&(!session.capturing&&clock()-session.baseTime>12||session.lastAudio&&clock()-session.lastAudio>3))stop();},1000);
  return {server,udp,close(){clearInterval(cleanup);stop();server.close();udp.close();}};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){const {values}=parseArgs({options:{origin:{type:'string',default:'http://127.0.0.1:4192'}}});const app=startBridge({pageOrigin:values.origin});console.log('键盘录音桥接已启动：本机HTTP4190 / 音频UDP17433（仅受信任局域网）。');for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>{app.close();process.exit(0);});}
