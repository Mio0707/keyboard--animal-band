import {FrameWindow} from './frame-window.js';
class BarCapture extends AudioWorkletProcessor {
  constructor(){
    super();this.window=null;this.cancelled=false;
    this.port.onmessage=({data})=>{
      if(data.type==='cancel'){this.cancelled=true;this.window=null;}
      if(data.type==='arm'){
        if(data.start<currentFrame||!Number.isSafeInteger(data.frames)||data.frames<=0||data.frames>sampleRate*120){this.port.postMessage({error:'录音起点已过或长度无效，请重试'});return;}
        this.window=new FrameWindow(data.start,data.frames);
      }
    };
  }
  process(inputs,outputs){
    if(this.cancelled)return false;
    const size=outputs[0]?.[0]?.length??inputs[0]?.[0]?.length??128;
    if(this.window&&this.window.add(inputs[0]??[],currentFrame,size)){
      const {data,inputFrames}=this.window;this.window=null;
      this.port.postMessage({samples:data,inputFrames},[data.buffer]);return false;
    }
    return true;
  }
}
registerProcessor('bar-capture',BarCapture);
