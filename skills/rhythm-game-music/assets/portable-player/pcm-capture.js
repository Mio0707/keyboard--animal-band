const loaded=new WeakMap();
export async function createCapture(ctx,input){
  if(!ctx.audioWorklet)throw Error('当前浏览器不支持精确录音，请使用Chrome或Edge打开本页');
  if(!loaded.has(ctx))loaded.set(ctx,ctx.audioWorklet.addModule(new URL('./pcm-capture-worklet.js',import.meta.url)).catch(e=>{loaded.delete(ctx);throw e;}));
  await loaded.get(ctx);
  const node=new AudioWorkletNode(ctx,'bar-capture',{numberOfInputs:1,numberOfOutputs:1,outputChannelCount:[1]});
  // The processor outputs silence: microphone audio is never monitored to speakers.
  input.connect(node);node.connect(ctx.destination);let rejectPending;
  return {
    record(start,frames){return new Promise((resolve,reject)=>{
      rejectPending=reject;node.onprocessorerror=()=>reject(Error('录音处理失败，请重试'));
      node.port.onmessage=({data})=>{if(data.error)reject(Error(data.error));else resolve(data);};
      node.port.postMessage({type:'arm',start:Math.round(start*ctx.sampleRate),frames});
    });},
    close(){node.port.postMessage({type:'cancel'});rejectPending?.(new DOMException('已取消录音','AbortError'));input.disconnect();node.disconnect();node.port.close();}
  };
}
