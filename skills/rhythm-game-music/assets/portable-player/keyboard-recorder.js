export const KEYBOARD_MIC='easyinput-wifi';
const base='http://127.0.0.1:4190';
export async function keyboardStatus(signal){
  const r=await fetch(base+'/status',{signal,cache:'no-store'});if(!r.ok)throw Error('键盘录音桥接不可用');return r.json();
}
export class KeyboardCapture{
  constructor(ctx){this.ctx=ctx;this.controller=new AbortController();this.level=0;this.done=false;}
  async post(path,body,signal=this.controller.signal){
    const r=await fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json','X-Keyboard-Token':this.token},body:JSON.stringify(body),signal});
    if(!r.ok){const error=await r.json();throw Error(error.error||'键盘录音失败');}return r;
  }
  async prepare(){
    let status;try{status=await keyboardStatus(this.controller.signal);}catch(e){if(e.name==='AbortError')throw e;throw Error('未连接本地键盘录音桥接，请启动桥接服务后刷新。');}
    if(!status.connected||!status.ready)throw Error('未收到键盘麦克风心跳，请检查键盘Wi-Fi和接收地址。');
    this.token=status.token;const ready=await(await this.post('/prepare',{})).json();this.lease=ready.lease;
    this.poll=setInterval(()=>keyboardStatus(this.controller.signal).then(s=>{this.level=s.level??0;}).catch(()=>{}),200);
  }
  async record(start,frames){
    const response=await this.post('/capture',{lease:this.lease,frames:Math.round(frames/this.ctx.sampleRate*16000),delay:Math.max(0,start-this.ctx.currentTime)});
    const decoded=await this.ctx.decodeAudioData(await response.arrayBuffer());
    if(Math.abs(decoded.length-frames)>1)throw Error('键盘录音长度不完整，请重试。');
    const samples=new Float32Array(frames);samples.set(decoded.getChannelData(0).subarray(0,frames));this.done=true;clearInterval(this.poll);this.level=0;
    return {samples,inputFrames:frames};
  }
  close(){clearInterval(this.poll);this.controller.abort();this.level=0;if(!this.done&&this.lease)this.post('/cancel',{lease:this.lease},null).catch(()=>{});}
}
