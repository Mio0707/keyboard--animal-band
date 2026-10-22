// Audio identity is verified at render/pack time; reject stale metadata on load too.
export function validateInstrumentConfig(m){
 if(!m.segments||!['theme','build','drop','hold'].every(k=>m.segments[k]))throw Error('缺少完整演奏段落');
 for(const id of ['dog','bear','cat','lion']){
  const s=m.renderSelection?.tracks?.[id];
  if(!s||!Number.isInteger(s.program)||m.programs?.[id]!==s.program)throw Error(`${id}音色配置不一致或缺失`);
  const sampled=s.renderEngine==='pitched-drum-sample',drum=id==='dog'||sampled;
  if(s.bank!==(drum?128:0)||s.channel!==(drum?9:0))throw Error(`${id}音色通道不一致`);
  if(sampled&&(s.sourceNote!==56||!s.noteSources?.['56']?.length))throw Error(`${id}牛铃源样本未经核实`);
 }
 return true;
}
