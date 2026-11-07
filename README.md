# One Last Kiss 编曲工程

一套从乐谱事件到 MIDI、采样分轨和人声混音的学习工程。项目以宇多田光的《One Last Kiss》与 Animenz 的钢琴编谱为参考，记录钢琴、国风、中西合奏和人声混音几版配器的实现。

## 工程结构

| 位置 | 内容 |
| --- | --- |
| `work/render_music.py` | 钢琴与室内乐采样渲染 |
| `work/guofeng/` | 笛箫、二胡、古筝配器及 Windows VST 渲染 |
| `work/fusion/` | 中西合奏编排、乐句交接和录音采样渲染 |
| `work/modal/`、`work/reeds/` | 调式与管乐配器实验 |
| `work/restore_dizi_xiao.py`、`work/repair_dizi_handoffs.py` | 恢复笛箫音色并补齐主旋律交接 |
| `work/vocal_merge/` | 节拍校正、人声对齐、动态处理和混音 |

## 从哪里开始

Python 3.11 或 3.12 可用于阅读和运行主要脚本。Windows 上调用 Kong Audio 旧版 VST 时，使用 32 位 Python 和与宿主同架构的 DLL。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

1. 阅读 `work/fusion/arrange_fusion.py`，了解乐谱事件如何分派到各声部。事件中的 `p` 是 MIDI 音高，`v` 是力度，`on` 和 `off` 以秒为单位。
2. 将拥有使用权限的乐谱事件和主旋律数据放在脚本期望的路径。Fusion 的输入为 `work/score_events.json` 与 `work/guofeng/arrangement.json`。该编排脚本按此曲的 120 小节结构编写。
3. 从素材来源取得所需音源，参照脚本中的 `sample_dir` 及 manifest 放置到本地。生成各乐器分轨后，才能运行依赖它们的后续版本。各版本的 `run.ps1` 是历史入口，需先补齐对应脚本、数据和采样。
4. 混音用到的人声和歌词可分别放在仓库根目录的 `inputs/vocal.mp4` 与 `inputs/source.lrc`。原项目以 112 BPM 校正伴奏，并按所用人声文件的实际剪裁补了约 20 秒。更换人声后应重新测量偏移。

在 FL Studio 中导入多轨 MIDI 后，需要自行给每个通道指定乐器。MIDI 保存音符、时值、力度等数据，GM 音色只是预览映射。不同阶段的 MIDI 保留各自的节拍与引子设置，人声混音版另做了时间校正。

## 素材来源

- 原曲与作词作曲为宇多田光。钢琴编谱参考 [Animenz 版本](https://www.mymusic5.com/animenzzz/46382)。
- 钢琴为 Alexander Holm 的 [Salamander Grand Piano v3](https://github.com/sfzinstruments/SalamanderGrandPiano)，使用 CC BY 3.0。
- 弦乐、部分管乐与打击乐来自 [VSCO 2 Community Edition](https://github.com/sgossner/VSCO-2-CE) 和 [VCSL](https://github.com/sgossner/VCSL)。
- 笛箫、二胡使用 [Kong Audio Mini DiZi 和 Mini ErHu](https://www.chineekong.com/free.htm)。古筝来自 [Pufermufin 的实录](https://freesound.org/people/Pufermufin/sounds/396868/)。
- 管乐实验的唢呐引用 [Francesc Fort / TaronjaSatsuma 的实录](https://commons.wikimedia.org/wiki/File:Suona.ogg) 及 [jiemojiemo 的持续音](https://freesound.org/people/jiemojiemo/sounds/514114/)。使用前请核对各来源的许可。

## 许可与发布范围

原创工程代码与文档采用 [CC BY 4.0](LICENSE.md)。原曲、原谱、歌词和第三方音源的许可独立。公开源码版提供实现与素材清单，运行所需的乐谱事件、MIDI、歌词、插件和录音需从获准使用的来源另行取得。
