// A tap toggles on release; a rotary gesture consumes the tap.
export class HeldTrackControls {
  constructor(){this.held=new Map();}
  down(code,track){if(!this.held.has(code))this.held.set(code,{track,used:false});}
  up(code,allowTap=true){
    const key=this.held.get(code);this.held.delete(code);
    return allowTap&&key&&!key.used?key.track:null;
  }
  turn(){
    const keys=[...this.held.values()];
    for(const key of keys)key.used=true;
    return keys.at(-1)?.track??null;
  }
  get selected(){return [...this.held.values()].at(-1)?.track??null;}
  clear(){this.held.clear();}
}
