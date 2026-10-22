import {validateInstrumentConfig} from './instrument-config.js';
import {DJTransport,TRACKS} from './dj-transport.js';
import {HeldTrackControls} from './held-track-controls.js';
import {BarSampler,barDuration,recordingFrames,nextBarTime,wavBlob} from './bar-sampler.js';
import {createCapture} from './pcm-capture.js';
import {KeyboardCapture} from './keyboard-recorder.js';
const $=s=>document.querySelector(s),status=t=>$('#status').textContent=t;
const catalog=await fetch('catalog.json',{cache:'no-cache'}).then(r=>r.json());
let ctx,filter,engine,sampler,recording=null,manifest,buffers,active,busy=false,revision=0,playing=false,prepared=[];
const held=new HeldTrackControls(),levels=Object.fromEntries(TRACKS.map(k=>[k,1])),gates=Object.fromEntries(TRACKS.map(k=>[k,true])),clips=new Map();
const styleNames={'swing-jazz':'Swing 爵士','drift-phonk':'Drift Phonk','jazz-funk':'爵士放克','bossa-nova':'Bossa Nova',electronic:'电子'};
for(const [i,item] of catalog.entries())$('#selection').add(new Option(`${item.title} / ${styleNames[item.style]??item.style}`,String(i)));
for(const [i,k] of TRACKS.entries()){
 const card=document.createElement('article');card.className='track';card.dataset.track=k;
 card.innerHTML=`<div class="meter" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div><button data-toggle="${k}" aria-pressed="true">${i+1} <span></span></button><input aria-label="声部音量" data-level="${k}" type="range" min="0" max="100" value="100"><output>100%</output>`;$('#tracks').append(card);
 card.querySelector('button').onclick=()=>toggle(k);card.querySelector('input').oninput=e=>volume(k,Number(e.target.value)/100);
}
function audio(resume=true){ctx??=new AudioContext();if(!filter){filter=ctx.createBiquadFilter();filter.type='lowpass';filter.frequency.value=18000;filter.connect(ctx.destination);sampler=new BarSampler(ctx,filter);}return resume?ctx.resume():Promise.resolve();}
const clipKey=()=>`${manifest.songId}:${manifest.bpm}:${manifest.beatsPerBar}`;
function stop(){revision++;busy=false;$('#play').disabled=!engine;engine?.stop();sampler?.stop();held.clear();playing=false;prepared=[];$('#play').textContent='开始演奏 · 空格';}
async function load(index){
 if(recording){status('请先完成或取消录音。');$('#selection').value=String(active);return;}
 stop();const id=revision;busy=true;$('#play').disabled=true;status('正在加载歌曲与分轨…');
 try{
  const item=catalog[index],base=new URL(item.base,location.href),m=await fetch(new URL('manifest.json',base),{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('清单加载失败');return r.json();});
  validateInstrumentConfig(m);
  m.sectionLabels={theme:'主题',build:'蓄力',drop:'高潮',hold:'等待',...m.sectionLabels};
  await audio(false);const decoded=Object.fromEntries(await Promise.all(Object.entries(m.segments).map(async([mode,s])=>[mode,Object.fromEntries(await Promise.all(TRACKS.map(async k=>{
   const url=new URL(s.assets[k].file,base);if(s.assets[k].sha256)url.searchParams.set('v',s.assets[k].sha256);const response=await fetch(url);if(!response.ok)throw Error('音频加载失败');const b=await ctx.decodeAudioData(await response.arrayBuffer());if(Math.abs(b.duration-s.duration)>1/44100)throw Error('分轨长度不一致');return[k,b];
  })))])));
  if(id!==revision)return;manifest=m;buffers=decoded;active=index;engine=new DJTransport(ctx,buffers,m.segments,filter,m.bpm,m.beatsPerBar);engine.volumes={...levels};engine.gates={...gates};
  $('h1').textContent=m.title;document.title=`${m.title} / ${styleNames[m.style]??m.style}`;$('#clock').textContent=`${styleNames[m.style]??m.style} · ${m.bpm} BPM · ${m.beatsPerBar}/4`;
  document.documentElement.style.setProperty('--accent',m.style==='drift-phonk'?'#ff8cc9':'#f6ca8e');
  for(const [i,k] of TRACKS.entries()){$(`[data-toggle="${k}"] span`).textContent=m.trackLabels[k];$(`[data-level="${k}"]`).setAttribute('aria-label',`${m.trackLabels[k]}音量`);}
  for(const [mode,key] of [['theme',5],['build',6],['drop',7]])$(`[data-mode="${mode}"]`).textContent=`${key} ${m.sectionLabels[mode]}${mode==='theme'?'':` · ${m.segments[mode].bars}小节`}`;
  $('#audition').href=new URL(m.preview.file,base).href;$('#download').disabled=!clips.has(clipKey());status('准备好了；切换风格会停止演奏，录音按歌曲和节拍保留。');
 }catch(e){if(id===revision){status(`${e.message}；可重新选择重试。`);$('#selection').value=String(active??index);}}
 finally{if(id===revision){busy=false;$('#play').disabled=!engine;}}
}
async function play(){if(busy||recording)return;await audio();if(playing){stop();return;}engine.start(prepared.length?prepared:'theme');prepared=[];playing=true;$('#play').textContent='停止演奏 · 空格';}
function toggle(k){gates[k]=!gates[k];engine?.setGate(k,gates[k]);$(`[data-track="${k}"]`).classList.toggle('muted',!gates[k]);$(`[data-toggle="${k}"]`).setAttribute('aria-pressed',String(gates[k]));}
function volume(k,v){levels[k]=Math.max(0,Math.min(1,v));engine?.setVolume(k,levels[k]);const card=$(`[data-track="${k}"]`);card.querySelector('input').value=String(Math.round(levels[k]*100));card.querySelector('output').textContent=`${Math.round(levels[k]*100)}%`;}
function section(mode){if(busy||recording)return;if(playing)engine.queue(mode);else if(mode==='theme')prepared=[];else prepared.push(mode);}
async function sample(){if(recording||busy)return;const clip=clips.get(clipKey());if(!clip){status('请先录音。');return;}await audio();const origin=engine?.current()?.start??ctx.currentTime;sampler.play(clip,nextBarTime(ctx.currentTime,origin,barDuration(manifest.bpm,manifest.beatsPerBar)));}
$('#play').onclick=play;$('#stop').onclick=stop;$('#sample').onclick=sample;$('#selection').onchange=e=>load(Number(e.target.value));
document.querySelectorAll('[data-mode]').forEach(e=>e.onclick=()=>section(e.dataset.mode));
$('#filter').oninput=e=>{if(filter)filter.frequency.setTargetAtTime(180*Math.pow(100,Number(e.target.value)/100),ctx.currentTime,.03);};
document.addEventListener('keydown',e=>{
 if(e.target.matches('input,select,textarea')||e.isComposing||e.metaKey||e.ctrlKey||e.altKey||e.shiftKey)return;
 const k=TRACKS[Number(e.key)-1];if(k){e.preventDefault();held.down(e.code,k);return;}if(e.repeat)return;
 if(e.code==='Space'){e.preventDefault();play();}else if(['5','6','7'].includes(e.key)){e.preventDefault();section({5:'theme',6:'build',7:'drop'}[e.key]);}else if(e.key==='8'){e.preventDefault();sample();}
 else if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();const track=held.turn(),d=e.key==='ArrowRight'?1:-1;if(track)volume(track,levels[track]+d*.05);else{$('#filter').value=String(Math.max(0,Math.min(100,Number($('#filter').value)+d*4)));$('#filter').dispatchEvent(new Event('input'));}}
 else if(e.key==='Enter'){e.preventDefault();$('#filter').value='100';$('#filter').dispatchEvent(new Event('input'));}
});
document.addEventListener('keyup',e=>{const k=held.up(e.code,!e.target.matches('input,select,textarea'));if(k)toggle(k);});window.addEventListener('blur',()=>held.clear());window.addEventListener('pagehide',()=>{stop();recording?.capture?.close();});
$('#record').onclick=async()=>{
 if(busy)return;if(recording){recording.cancelled=true;recording.capture?.close();status('正在取消录音…');return;}
 const job={};recording=job;$('#selection').disabled=true;$('#record').textContent='取消录音';sampler?.stop();
 try{
  await audio();const frames=recordingFrames(ctx.sampleRate,manifest.bpm,manifest.beatsPerBar,Number($('#bars').value));
  if($('#mic').value==='keyboard'){job.capture=new KeyboardCapture(ctx);await job.capture.prepare();}
  else{job.stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false}});job.capture=await createCapture(ctx,ctx.createMediaStreamSource(job.stream));}
  if(job.cancelled)throw new DOMException('录音已取消','AbortError');
  const start=playing?nextBarTime(ctx.currentTime,engine.current()?.start??ctx.currentTime,barDuration(manifest.bpm,manifest.beatsPerBar)):ctx.currentTime+.25;
  status(`录音 ${frames/ctx.sampleRate} 秒；伴奏保持当前状态。`);const data=await job.capture.record(start,frames);if(data.inputFrames<frames)throw Error('录音输入不完整');const clip=ctx.createBuffer(1,frames,ctx.sampleRate);clip.copyToChannel(data.samples,0);clips.set(clipKey(),clip);$('#download').disabled=false;status('录音完成，按8回放；刷新前请下载。');
 }catch(e){status(e.message);}finally{job.capture?.close();job.stream?.getTracks().forEach(t=>t.stop());recording=null;$('#selection').disabled=false;$('#record').textContent='录音';}
};
$('#download').onclick=()=>{const clip=clips.get(clipKey());if(!clip)return;const url=URL.createObjectURL(wavBlob(clip)),a=document.createElement('a');a.href=url;a.download=`${manifest.songId}-${manifest.bpm}bpm.wav`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
function frame(){
 const now=ctx?.currentTime??0,current=playing?engine?.current():null,mode=current?.mode??'theme';$('#section').textContent=current?manifest.sectionLabels[mode]:'待演奏';
 if(manifest){const seconds=manifest.segments[mode].duration,local=current?(now-current.start+current.offset)%seconds:0;$('#progress').value=local/seconds;$('#position').textContent=current?`第 ${Math.floor(local/barDuration(manifest.bpm,manifest.beatsPerBar))+1} / ${manifest.segments[mode].bars} 小节`:'';const queue=playing?engine.groups.filter(g=>g.start>now&&['build','drop'].includes(g.mode)).map(g=>g.mode):prepared;$('#queue').textContent='接下来：'+queue.map(k=>manifest.sectionLabels[k]).concat('主题循环').join(' → ');}
 for(const k of TRACKS){let rms=0;const meter=current?.meters?.[k];if(meter&&gates[k]){meter.node.getFloatTimeDomainData(meter.samples);rms=Math.sqrt(meter.samples.reduce((a,x)=>a+x*x,0)/meter.samples.length);}const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;document.querySelectorAll(`[data-track="${k}"] .meter i`).forEach((e,i)=>e.style.height=`${reduced?10:Math.min(100,8+rms*(700+i*180))}%`);}
 requestAnimationFrame(frame);
}
await load(0);requestAnimationFrame(frame);
