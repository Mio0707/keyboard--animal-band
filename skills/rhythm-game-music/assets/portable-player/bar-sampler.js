export function barDuration(bpm,beatsPerBar=4){
  if(!(bpm>0&&beatsPerBar>0))throw Error('速度或拍号无效');
  return 60*beatsPerBar/bpm;
}
export function nextBarTime(now,origin,seconds,lead=.15){
  return origin+Math.max(0,Math.ceil((now+lead-origin)/seconds))*seconds;
}
export function recordingFrames(sampleRate,bpm,beatsPerBar,bars){
  if(![1,2,4,8].includes(bars))throw Error('请选择1、2、4或8小节');
  return Math.round(sampleRate*barDuration(bpm,beatsPerBar)*bars);
}
export class BarSampler {
  constructor(ctx,destination){this.ctx=ctx;this.destination=destination;this.voices=[];}
  play(buffer,at){
    this.voices=this.voices.filter(v=>v.end>this.ctx.currentTime);
    const last=this.voices.at(-1);at=Math.max(at,last?.end??0);
    const source=this.ctx.createBufferSource(),gain=this.ctx.createGain();
    source.buffer=buffer;gain.gain.value=.8;source.connect(gain);gain.connect(this.destination);
    const voice={source,gain,start:at,end:at+buffer.duration};this.voices.push(voice);
    source.onended=()=>{source.disconnect();gain.disconnect();this.voices=this.voices.filter(v=>v!==voice);};
    source.start(at);return voice;
  }
  stop(){for(const v of this.voices){try{v.source.stop();}catch{}v.source.disconnect();v.gain.disconnect();}this.voices=[];}
}
export function wavBlob(buffer){
  const length=buffer.length,rate=buffer.sampleRate,data=new ArrayBuffer(44+length*2),v=new DataView(data);
  const text=(at,s)=>[...s].forEach((c,i)=>v.setUint8(at+i,c.charCodeAt(0)));
  text(0,'RIFF');v.setUint32(4,36+length*2,true);text(8,'WAVE');text(12,'fmt ');
  v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,rate,true);v.setUint32(28,rate*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);text(36,'data');v.setUint32(40,length*2,true);
  const samples=buffer.getChannelData(0);
  for(let i=0;i<length;i++){const x=Math.max(-1,Math.min(1,samples[i]));v.setInt16(44+2*i,Math.round(x*(x<0?32768:32767)),true);}
  return new Blob([data],{type:'audio/wav'});
}
