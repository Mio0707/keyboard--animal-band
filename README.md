# Keyboard × Animal Band · 歌曲改编演奏 Skill

输入歌曲和目标风格，让支持本地工具的 AI Agent 完成曲谱核对、风格编配、音色选择、渲染与检查，输出可用 EasyInput 八键和旋钮操作的演奏网页。

## 下载与安装

- **[下载 Skill ZIP](downloads/rhythm-game-music.zip)**：解压得到 `rhythm-game-music` 文件夹，将整个文件夹放进你的 AI Agent 的 skills 目录。不要只复制 `SKILL.md`，脚本、参考资料和网页模板都是运行所需文件。
- **[查看 Skill 源目录](skills/rhythm-game-music)**：采用标准 `SKILL.md` 结构；实际安装目录和调用语法以你使用的 Agent 为准。Agent 需要能联网检索、读写本地文件及运行 Python／本地命令。只支持聊天或上传附件的客户端不能直接执行本地渲染。

在 Codex 中，可以直接让 Agent：

> 从 https://github.com/Mio0707/keyboard--animal-band 的 skills/rhythm-game-music 安装这个 Skill。

安装后调用：

> 使用 $rhythm-game-music，把《弥渡山歌》改编成 Swing 爵士和 Drift Phonk，输出能用 EasyInput 八键及旋钮操作的网页，并启动本地试听。

其他兼容 Agent 可直接说“使用 rhythm-game-music”，或按其 Skill 调用方式执行。首次调用让 Agent 检查并准备依赖。

## 会得到什么

- 同一首歌曲的不同风格可合并到一个演奏页，支持声部开关、独立音量、按次排队的段落及整小节录音回放。
- 可编辑源谱、显式编曲谱、分轨 WAV／MIDI、试听混音，以及音频与动作事件的校验结果。
- Mac 的 `启动演奏.command`、Windows 的 `启动演奏.bat` 和通用 `start.py`。保持启动窗口打开；端口被占用时自动选空闲端口。

默认输出轻量通用演奏网页。动物舞台是可选适配层，本 Skill 包不包含项目专用动物图集；新乐器需匹配对应人物，不能直接套用无关动作。

## 实体键盘操作

先在 EasyInput 中把 KEY1–8 设置为普通数字 1–8，旋钮左／右设置为方向键 ←／→，按下设置为 Enter。键盘需能上报按住按键时同时旋转的输入。连接后点击演奏页。

| 操作 | 功能 |
| --- | --- |
| KEY1–4 | 开关鼓、和声、低音、旋律声部 |
| 按住 KEY1–4 ＋旋钮 | 调整对应声部音量 |
| 旋钮／按下 | 调整滤波／复位滤波 |
| KEY5 | 回主题 |
| KEY6／KEY7 | 每按一次追加一段，默认各 4 小节；按顺序播完回主题 |
| KEY8 | 回放自己的录音 |
| 空格 | 开始／停止 |

没有硬件时可先用电脑键盘测试。键盘麦克风是独立能力，需要兼容固件、网络配置和 Node.js 桥接；启动器会打印 `node keyboard-audio-bridge.mjs --origin 实际网页地址` 命令。数字按键可用不代表麦克风已经连接。当前播放器声音由电脑输出，未接入键盘扬声器播放。

## 依赖与能力边界

- **制作端**：Python 3.10+、NumPy、FluidSynth，以及你有权使用的 SF2／SF3 音源；键盘麦克风桥接另需 Node.js 18+。Skill 不附带第三方音源、用户录音、Wi-Fi 凭据或本机库存快照。
- **演奏端**：已渲染的网页只需 Python 3 和现代浏览器；使用麦克风时需允许录音权限。
- **歌曲输入**：可核对曲谱／单旋律 MIDI，固定速度的 2/4、3/4、4/4。仅有歌名时由 Agent 查谱；找不到谱或版本不清时需要补充材料。目前没有任意音频自动准确扒谱功能。
- **风格支持**：附电子、爵士放克、Bossa Nova、Swing 爵士、Drift Phonk 等专业路线与实际音色选择。内置可生成候选音符的 starter 为 Swing 爵士和 Drift Phonk；其他风格由 Agent 按资料编写显式谱面，再复用渲染、检查与网页打包流程。不是只替换风格名称。
- **验收范围**：自动检查能验证拍长、文件、削波、实际 MIDI 音色和动作来源；音乐识别度、风格表现和实体硬件体验仍需试听／实测。当前测试是在同一电脑独立目录完成，未声称跨机器或所有 Agent 均验收通过。

## 维护与验证

```sh
python3 -m pip install -r skills/rhythm-game-music/requirements.txt
python3 -B -m unittest discover -s skills/rhythm-game-music/scripts -p 'test_*.py'
node --test skills/rhythm-game-music/scripts/test_keyboard_bridge.mjs
```

不带本机音源库存时，音色库集成测试会明确跳过；其他测试可独立运行。完整渲染还需要准备实际音源和 FluidSynth，执行方法见 [歌曲到演奏交付](skills/rhythm-game-music/references/song-input-performance.md)。
