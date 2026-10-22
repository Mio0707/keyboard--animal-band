# 换一首歌曲：谱面、改编、渲染、演奏

适用于用户要求“改编某首歌曲并用键盘演奏”，包含可迁移脚本和轻量演奏页，不依赖《茉莉花》工程。AI负责来源核对、转谱与音乐判断，代码负责时间、音色、渲染、验证和打包。不要把 starter 输出当成审美完成品。

## 输入边界

- 歌名／链接：查可靠曲谱，优先教材、原作者或机构刊载版本；确认具体版本，保存来源。图片谱由AI读取后逐句核对，疑点记录为待确认，不编造已听辨。生成原旋律 MIDI/试听用于核对；版本清楚时继续编配，不强制等待用户逐步确认。
- MIDI：`song_bundle.py import-midi` 支持SMF0/1、PPQ、单一速度和拍号。选择单旋律通道；复调、变速和混合拍号明确报错，不能静默抹掉。导入后仍需补和声、乐句和来源。
- 简谱／MusicXML：转成下面统一模型并检查时值；装饰音、自由延长、转调和弱起必须明确如何保留或简化。MusicXML目前由AI或项目已有工具转写，没有自动导入器。
- 只有音频：本工具不提供自动扒谱或分轨。先找到可靠谱面，或使用实际可用的转录工具并校对；找不到时向用户索取旋律／MIDI，不能伪称任意MP3已准确识谱。

## 统一歌曲文件 song.json

必需：`id,title,bpm,beatsPerBar,beats,source,melody,chords`。时间单位为四分音符拍；MIDI音高为整数，休止通过空隙表示。支持固定速度、2/4、3/4、4/4；目前不自动处理6/8或变速图。拍号转换需显式说明，如把原2/4两个小节归为演奏4/4一小节，不能默默把旋律拉长一倍。

```json
{
  "version":1,"id":"new-tune","title":"新旋律","bpm":105,"beatsPerBar":4,"beats":8,
  "source":{"file":"my-melody.mid","description":"user melody; harmony newly authored"},
  "phraseEnds":[4,8],"hookStart":0,
  "melody":[{"midi":69,"beat":0,"duration":1},{"midi":72,"beat":1,"duration":1},{"midi":76,"beat":2,"duration":2},{"midi":72,"beat":4,"duration":1},{"midi":69,"beat":5,"duration":3}],
  "chords":[{"name":"Am9","beat":0,"duration":8,"root":45,"voicing":[55,59,60,64]}]
}
```

和声是实际根音和voicing，不靠字符串名称猜和弦。chords连续覆盖总长度；曲尾休止也属于总长度。完整主题保留原曲引腔和尾声。实时演奏默认将KEY6/KEY7写成4小节独立短句，每按一次追加一遍；用`performanceClipBars`显式选择其他长度，不能自动把KEY7设置成两遍全曲。`hookStart`指定适合提取短句的源谱起点；4小节需要重写结尾与呼吸，不能直接裁剪长音频。

## 从一句话到网页的交付约定

用户输入例：`用 $rhythm-game-music，把《歌曲名》改编成 Bossa Nova，输出能用 EasyInput 八键和旋钮演奏的网页。` 歌名与风格是用户输入；源谱整理、和声、真实音色选择、合奏检查和启动服务由执行Skill的AI完成。多种风格分别写谱／渲染，通过同一次pack合并成一个页面。旋律来源缺失时不能用一首无关的生成旋律冒充原曲。

曲谱与编曲定稿后，可用统一build串联渲染→实际音色／动作检查→网页打包：

```sh
python3 "$SKILL/scripts/song_bundle.py" build "$PROJECT/song.json" --style bossa-nova --arrangement "$PROJECT/arrangement.json" --sound-plan "$PROJECT/sound-plan.json" --soundfont "$SOUNDFONT" --fluidsynth "$FLUIDSYNTH" --output "$PROJECT/export"
python3 "$PROJECT/export/performance/start.py"
```

`--arrangement`省略时只支持已有swing-jazz／drift-phonk starter。其他风格必须先按专业路线编写完整显式谱面；没有对应风格资料时先补可核实依据，不能悄悄改成已有风格。build检查歌曲、谱面、音色方案属于同一请求。交付网页所在文件夹或ZIP、可访问本地URL、可编辑源谱及简短验证结果；本地URL仅当前运行机器有效，不当作公网发布链接。

生成目录附带Mac／Windows启动脚本与start.py。启动器自动选择可用本地端口并打开浏览器，窗口保持打开；播放端只需Python3和现代浏览器，不再需要渲染器或外部音源。页面写明硬件映射：KEY1–8普通数字1–8，旋钮←／→，短按Enter。需要硬件支持按住＋旋转的重叠输入；未连接真实设备时报告网页／事件层验证，不声称实体测试通过。录音桥接与键位输入分别验收。

## 最短执行链

以下路径由实际机器探测／用户提供，不读取案例电脑的库存路径。`SKILL`表示当前skill目录，`PROJECT`表示新歌曲工作目录，命令中的路径替换为实际值。

```sh
python3 "$SKILL/scripts/song_bundle.py" doctor --fluidsynth "$FLUIDSYNTH" --soundfont "$SOUNDFONT"
python3 "$SKILL/scripts/song_bundle.py" import-midi melody.mid --channel 0 --title 新歌曲 --id new-song --output "$PROJECT/song.json"
python3 "$SKILL/scripts/song_bundle.py" validate "$PROJECT/song.json"
python3 "$SKILL/scripts/sound_library.py" scan --soundfont "$SOUNDFONT" --output "$PROJECT/catalog.json"
python3 "$SKILL/scripts/sound_library.py" plan --catalog "$PROJECT/catalog.json" --style swing-jazz --output "$PROJECT/sound-plan.json"
python3 "$SKILL/scripts/song_bundle.py" arrange "$PROJECT/song.json" --style swing-jazz --output "$PROJECT/arrangement.json"
python3 "$SKILL/scripts/song_bundle.py" render "$PROJECT/arrangement.json" --sound-plan "$PROJECT/sound-plan.json" --soundfont "$SOUNDFONT" --fluidsynth "$FLUIDSYNTH" --pilot --output "$PROJECT/pilot"
# 检查完整乐句及四组组合试听，按实际问题编辑arrangement.json，再正式渲染。
python3 "$SKILL/scripts/song_bundle.py" render "$PROJECT/arrangement.json" --sound-plan "$PROJECT/sound-plan.json" --soundfont "$SOUNDFONT" --fluidsynth "$FLUIDSYNTH" --output "$PROJECT/final"
python3 "$SKILL/scripts/song_bundle.py" verify-bundle "$PROJECT/final"
python3 "$SKILL/scripts/song_bundle.py" pack --output "$PROJECT/performance" "$PROJECT/final"
python3 -m http.server 4192 --bind 127.0.0.1 --directory "$PROJECT/performance"
```

`import-midi`不是每次必跑：图片／简谱已转成song.json时跳过。渲染需Python3、NumPy、FluidSynth及用户实际可用的SF2/SF3；不要打包外部音源。播放器仅需本地HTTP与现代浏览器。键盘麦克风额外需要Node.js运行输出目录的keyboard-audio-bridge.mjs，并按当前硬件协议配置接收地址；桥接默认允许http://127.0.0.1:4192，演奏页端口变化时使用`node keyboard-audio-bridge.mjs --origin 实际网页origin`（地址不含末尾斜杠），启动器会打印对应命令；没有真实心跳时只交付桥接能力，不声称麦克风已验收。

starter目前实现 `swing-jazz` 与 `drift-phonk`：根据输入旋律和显式和声生成候选，绝非覆盖所有爵士／Phonk。其他流派用已有专业路线和音色profile，AI编写同契约的`sectionScores`，继续复用render/verify/pack；不要对着另一首歌硬套案例音符。任何流派均可在`arrangement.json`逐音修改，渲染器不重新生成／覆盖人工改谱。

## 可演奏资产与验收

- `sectionScores`按`theme/build/drop/hold`保存`bars`与四条轨的显式音符；每音`midi,beat,duration,velocity,channel`，鼓通道9，其他谱面通道0。四条轨代表鼓、和声、低音、旋律职责，不限动物造型。
- 自编其他流派的recipe顶层保留`songId,title,style,bpm,beatsPerBar,source,sourceScore,sectionScores,trackLabels,sectionLabels,design`；`sourceScore`是完整song.json，`design.mixLevels`是四轨线性增益。可从starter生成的JSON取得结构，再按目标流派改写实际音符和元数据，不能只换style字符串。演奏用正式包应提供四个段落；`--pilot`仅导出主题，不能将小样当完整演奏包。
- `verify-bundle`及pack内置`instrument_contract.py`检查：每段实际发声MIDI预设必须匹配音色清单，复用段也检查；静音不算换乐器；移调牛铃核对源样本MIDI与哈希，避免把其控制谱当成钢琴。加载页还拒绝缺失／冲突音色配置。动物舞台另外核对形态与音色，不能用视觉覆盖掩盖错误音频。
- render统一导出分轨、混音、MIDI、组合试听、原音色记录、精确note-on/hold事件与SHA256；牛铃使用经核实的源鼓键移调，不把旋律音高直接当鼓键。
- pack内置通用演奏页，读取catalog而非固定歌曲路径；1–4开关、按住＋旋钮调音量、5回主题、6/7按次排队、8录音回放。录音不启动伴奏。不同歌曲／节拍的录音分开保留，未实现时间伸缩或自动调性适配；刷新前下载。
- 本项目动物舞台是可选产品适配层。要接入现有舞台，再登记歌曲、风格和允许的速度／拍号，检查真实音色对应形态；没有新形态时明确缺口，不给铜管套吉他动作。不能因轻量演奏页可用就声称所有动物动画已通用化。
- 保留一个可公开分享的Skill压缩包，排除`__pycache__`、本机库存快照、密钥、用户录音及外部音源。发布前至少用第二首真实歌曲及不同拍号／速度的独立小谱验证；换目录通过不能冒称换机器验证。

## 本次实践形成的修正

《弥渡山歌》采用人民日报海外版2016-12-22第06版刊载谱；保留主音与句法，省略装饰音和自由延长，2/4归组4/4，112 BPM。初版KEY7重复主题两遍导致单次约43秒，用户反馈不适合按次排队；现改为完整主题10小节、KEY6/KEY7各4小节，后者从主体短句重写。两版以原旋律重演，不复用网络上现成Phonk录音。来源转录仍需用户确认识别度；技术检查不能为转谱或听感自动背书。

段落相似时，可用`scripts/performance_sections.py`的`rewrite`生成可编辑候选：原声类间奏让领奏退出并交接职责，Phonk间奏撤走底鼓与低音，4小节变奏恢复完整律动。不是只改变力度。`render --reuse-from 旧包`可按recipe的`reuseSections`原样复制已认可主题／等待段，并检查谱面、时钟和音源哈希；渲染到新目录，验证后再替换。
