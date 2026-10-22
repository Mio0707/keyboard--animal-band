# 从流派与奏法选到实际音色，再交给渲染器

## 文件分工

- [style-production.md](style-production.md)：读目标路线的编曲、配器与限制。
- [style-sound-profiles.json](../assets/style-sound-profiles.json)：10条可调整的候选路线；包含职责、奏法、建议音域、实际bank/program候选、鼓键。不是全曲自动编曲器。
- `data/local-sound-library.json`：开发机可选库存快照，含SoundFont实际preset/key zones、文件SHA256，以及网页采样文件的存在性/SHA256。分享包不携带此本机文件；换机器、换源或加样本时重新扫描，不把本机路径当通用路径。
- `scripts/sound_library.py`：scan/plan/verify，标准库即可运行；不自动下载、安装或花钱买音源。

## 本机已核实的范围

MuseScore General.sf3：实际309个preset，含bank0通用乐器、bank128多种鼓组，以及额外表达/弦乐bank。`specialArticulations=unverified`表示“名称或zone存在”，不代表真实奏法、力度层次、连奏或审美已试听。

Animal Band网页采样包：31个MP3、4类声部（钢琴、指弹贝斯、Alto Sax及5种鼓声）。它是从音源制作的有限子集，不等于SoundFont全部309个preset；例如网页包没有尼龙吉他、刷奏或Pandeiro。

网页包的playableRange、原始采样音高和maxPitchShiftSemitones是播放约束；不能拿单个萨克斯采样无限移调冒充其他乐器。此轮选择器接通的是离线SoundFont渲染，网页采样库存为诊断资料，未改造网页采样引擎。

本次未核实到Pandeiro专项样本/映射；SoundFont内部instrument/sample名称也无Pandeiro名称命中，但不能据名称穷尽证明所有未命名采样都不存在。**因此状态是“没有经核实的专项映射”，不能自动用GM54铃鼓、60/61邦戈、62–64康加换名。**

## 最短工作流程

```sh
python3 scripts/sound_library.py scan --soundfont /实际路径/音源.sf3 --web-library /实际路径/sample-library.json --output /实际路径/catalog.json
python3 scripts/sound_library.py plan --catalog /实际路径/catalog.json --style bossa-nova --output /项目路径/sound-plan.json
python3 scripts/sound_library.py verify /项目路径/sound-plan.json --soundfont /实际路径/音源.sf3
```

只看目标profile和输出清单，不必把309条全部塞进上下文。需要替代时，在本路线候选中按实际有无选择；缺核心乐器要明确改路线/补音源，不静默选一个“差不多”的别名。`--require pandeiro`在目前缺专项映射时明确失败。可选缺口只在gaps中报告，不阻塞可用路线。

生成清单逐轨记录role/performance、preset真实名、SoundFont SHA256、bank、**零基**program/channel、允许鼓键。建议音域不是一刀切禁区，但谱面超出真实zone、网页移调上限或实际演奏范围需处理。

## 渲染接入

当前项目共享渲染器已支持：

```sh
python3 render_bossa_nova_v2.py --sound-plan /项目路径/sound-plan.json --fluidsynth /实际路径/fluidsynth --soundfont /实际路径/音源.sf3
```

同样作用于复用render_jazz_funk.py的爵士/Bossa生成器。它在渲染前校验SHA256和actual preset，设置实际Program Change，按选定允许键检查鼓谱；输出manifest.renderSelection记录清单与实际preset名。

支持范围明确为旋律bank0/channel0和打击bank128/channel9。鼓组bank128通过FluidSynth默认打击通道及对应program选择；不是CC0直接写128。其他bank目前拒绝，不以加载成功代替选对音色。官方API另提供按SoundFont ID/bank/program显式选择：[FluidSynth文档](https://www.fluidsynth.org/api/group__midi__messages.html)。

没有--sound-plan时保留原工程行为，不擅自覆盖已有渲染、用户录音或键盘设置。Sound plan只选音色，不自动把现有乐谱的节奏、和声或音域改成所选流派；需要用目标profile的奏法意图重新写谱，并逐句验证。

本次通过真实zone→instrument→sample关系核实Brush鼓组：37对应`Misc. Percussion / Rim Tap`，38对应`Brush Snares / Brush Snr 1`，42对应`Hi Hats Treb / Hi-Hat Closed`。这是本机该SHA256音源的映射，不是所有鼓库的通则。清单noteSources保留原始名称证据，仍需试听实际效果。

## 探针与验收

项目`scripts/render_sound_plan_probe.py`可用同一清单渲染5秒中性短句，证明所选音色能发声、MIDI/manifest按清单记录。它**不是曲风演示或专业音色品质认证**。先探针再目标小样，最后合奏试听。

记录三个不同状态：库存/映射可用；技术渲染通过；具体奏法及风格已试听。后一个状态不能从前两个自动推导。尤其Brush kit的名字不能证明每个鼓键都是刷子，GM吉他也不自带真实指弹动作。
