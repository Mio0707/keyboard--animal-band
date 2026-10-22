import {barDuration} from './bar-sampler.js';
export const TRACKS = ['dog','bear','cat','lion'];

export class DJTransport {
  constructor(ctx, buffers, segments, destination, bpm=96,beatsPerBar=4) {
    this.ctx=ctx;this.buffers=buffers;this.segments=segments;this.destination=destination;
    this.barSeconds=barDuration(bpm,beatsPerBar);this.groups=[];this.events=[];
    this.gates=Object.fromEntries(TRACKS.map(k=>[k,true]));
    this.volumes=Object.fromEntries(TRACKS.map(k=>[k,1]));
    this.pendingUntil=0;
  }
  current(time=this.ctx.currentTime) {
    return this.groups.filter(g=>g.start<=time&&g.end>time).at(-1)??null;
  }
  create(mode,start,offset=0) {
    const spec=this.segments[mode];
    const output=this.ctx.createGain();output.connect(this.destination);
    output.gain.setValueAtTime(0,start);output.gain.linearRampToValueAtTime(1,start+.005);
    const group={mode,start,end:['build','drop'].includes(mode)?start+spec.duration-offset:Infinity,offset,nodes:[],gains:{},volumes:{},meters:{},output};
    for(const id of TRACKS) {
      const source=this.ctx.createBufferSource(),gain=this.ctx.createGain(),volume=this.ctx.createGain();
      source.buffer=this.buffers[mode][id];source.loop=!['build','drop'].includes(mode);
      source.loopStart=0;source.loopEnd=spec.duration;
      gain.gain.setValueAtTime(0,start);
      gain.gain.linearRampToValueAtTime(this.gates[id]?1:0,start+.005);
      volume.gain.setValueAtTime(this.volumes[id],start);
      source.connect(gain);gain.connect(volume);
      let meter;
      if(this.ctx.createAnalyser){meter=this.ctx.createAnalyser();meter.fftSize=256;meter.smoothingTimeConstant=.7;volume.connect(meter);meter.connect(output);group.meters[id]={node:meter,samples:new Float32Array(256)};}
      else volume.connect(output);
      source.start(start,offset);if(Number.isFinite(group.end))source.stop(group.end);
      source.onended=()=>{source.disconnect();gain.disconnect();volume.disconnect();meter?.disconnect();};
      group.nodes.push(source);group.gains[id]=gain;group.volumes[id]=volume;
    }
    this.groups.push(group);
    return group;
  }
  stopGroup(group,at) {
    group.end=Math.min(group.end,at);
    if(group.start<at-.01){
      group.output.gain.setValueAtTime(1,at-.008);
      group.output.gain.linearRampToValueAtTime(0,at);
    }
    // A future clip can be cancelled before it makes any sound.
    for(const node of group.nodes)node.stop(Math.max(at,this.ctx.currentTime));
  }
  start(playlist='theme') {
    this.stop();const at=this.ctx.currentTime+.08;
    const modes=Array.isArray(playlist)?playlist:[playlist];
    let cursor=at;
    for(const mode of modes){
      if(!['build','drop'].includes(mode))continue;
      const group=this.create(mode,cursor);cursor=group.end;
    }
    this.create('theme',cursor);
    this.events.push({action:'start',playlist:modes,time:at});return at;
  }
  queue(mode) {
    const now=this.ctx.currentTime;
    const active=this.current();
    // Append after every finite performance clip, including clips not yet started.
    const tail=this.groups.filter(g=>Number.isFinite(g.end)&&g.end>now+.02).at(-1);
    const at=mode!=='theme'&&tail?tail.end
      :active?Math.max(now+.02,active.start+(Math.floor((now-active.start+.06)/this.barSeconds)+1)*this.barSeconds)
      :now+.08;
    const remaining=[];
    for(const group of this.groups){
      if(group.start>=at){this.stopGroup(group,now);continue;}
      if(group.end>at)this.stopGroup(group,at);
      remaining.push(group);
    }
    this.groups=remaining;
    const group=this.create(mode,at);
    if(mode!=='theme')this.create('theme',group.end);
    this.events.push({action:mode==='theme'?'return-theme':'enqueue',mode,time:at});return at;
  }
  setGate(id,on) {
    const active=this.current();
    const now=this.ctx.currentTime;
    const at=active?active.start+(Math.floor((now-active.start+.06)/this.barSeconds)+1)*this.barSeconds:now;
    this.gates[id]=on;
    for(const group of this.groups) {
      if(group.end<=at)continue;
      const parameter=group.gains[id].gain;
      // Cancel only future automation, preserving an already sounding gain.
      parameter.cancelScheduledValues(Math.max(at,group.start+.006));
      parameter.setTargetAtTime(on?1:0,Math.max(at,group.start+.006),.008);
    }
    this.events.push({action:'gate',track:id,on,time:at});return at;
  }
  setVolume(id,value) {
    if(!TRACKS.includes(id)||!Number.isFinite(value))return;
    const level=Math.max(0,Math.min(1,value)),now=this.ctx.currentTime;
    this.volumes[id]=level;
    for(const group of this.groups){
      if(group.end<=now)continue;
      const parameter=group.volumes[id].gain;
      parameter.cancelScheduledValues(now);
      if(group.start>now)parameter.setValueAtTime(level,group.start);
      else parameter.setTargetAtTime(level,now,.02);
    }
    this.events.push({action:'volume',track:id,value:level,time:now});
  }
  stop() {
    for(const group of this.groups)for(const node of group.nodes){try{node.stop();}catch{}node.disconnect();}
    for(const group of this.groups){for(const gain of [...Object.values(group.gains),...Object.values(group.volumes),...Object.values(group.meters).map(m=>m.node)])gain.disconnect();group.output.disconnect();}
    this.groups=[];this.pendingUntil=0;
  }
}
