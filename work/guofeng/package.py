from pathlib import Path
import json,shutil,zipfile,subprocess,struct,math
import numpy as np,soundfile as sf,imageio_ffmpeg
R=Path(__file__).resolve().parent;O=R.parent.parent/'outputs/Guofeng';P=O/'Python_Project';P.mkdir(exist_ok=True)
report=json.loads((O/'render_report.json').read_text())
arr=json.loads((R/'arrangement.json').read_text());bad={}
for key,file in [('wind','dizi_xiao.wav'),('erhu','erhu.wav')]:
 x,sr=sf.read(R/file,dtype='float32');silent=[]
 for n in arr[key]:
  lo=int((n['on']+.02)*sr);hi=int(min(n['off'],n['on']+.25)*sr);z=x[lo:hi]
  rms=float(np.sqrt(np.mean(z*z))) if len(z) else 0
  if rms<.00005:silent.append([n['bar'],n['p']])
 bad[key]=silent
assert not any(bad.values()),bad
report['silent_planned_note_checks']=bad
pr=report['stems']['05_piano_support']['rms'];gr=report['stems']['03_guzheng']['rms']
report['piano_rms_db_below_guzheng']=20*math.log10(gr/pr)
report['source_links']={'dizi_erhu':'https://www.chineekong.com/free.htm','guzheng':'https://freesound.org/people/Pufermufin/sounds/396868/','gong_wood':'https://github.com/sgossner/VCSL','piano':'https://github.com/sfzinstruments/SalamanderGrandPiano'}
(O/'render_report.json').write_text(json.dumps(report,indent=2))
# Editable standard MIDI for the orchestration, using an external VST for final sound.
def vlq(n):
 out=[n&127];n>>=7
 while n:out.insert(0,(n&127)|128);n>>=7
 return bytes(out)
def track(label,events):
 out=b'\0\xff\x03'+vlq(len(label))+label;last=0
 for t,msg in sorted(events,key=lambda x:x[0]):
  tick=max(0,round(t*960*2));out+=vlq(tick-last)+msg;last=tick
 out+=b'\0\xff\x2f\0';return b'MTrk'+struct.pack('>I',len(out))+out
tracks=[]
tracks.append(track(b'Tempo',[(0,b'\xff\x51\x03\x07\xa1\x20')]))
for channel,key in enumerate(['wind','erhu','guzheng','piano']):
 ev=[]
 if key in ['wind','erhu']:
  for n in arr[key]:ev.extend([(n['on'],bytes([0x90+channel,n['p'],n['v']])),(n['off'],bytes([0x80+channel,n['p'],0]))])
 else:
  for n in arr[key]:ev.extend([(n['on'],bytes([0x90+channel,n['p'],n['v']])),(n['on']+n['gate'],bytes([0x80+channel,n['p'],0]))])
 tracks.append(track(key.encode(),ev))
(O/'Guofeng_Arrangement.mid').write_bytes(b'MThd'+struct.pack('>IHHH',6,1,len(tracks),960)+b''.join(tracks))
for name in ['arrange.py','vst_host.py','render_mix.py','arrangement.json','dizi_xiao_plan.json','erhu_plan.json','guzheng_manifest.json','percussion_manifest.json']:
 shutil.copy2(R/name,P/name)
shutil.copy2(R.parent/'score_events.json',P/'score_events.json')
for sub in ['guzheng','percussion']:
 shutil.copytree(R/'samples'/sub,P/'samples'/sub,dirs_exist_ok=True)
for old in report['used_local_samples']:
 path=Path(old)
 if path.suffix=='.flac':dest=P/'samples/piano'/path.name
 elif path.name.startswith('bdrum'):dest=P/'samples/drum'/path.name
 else:continue
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
lic=P/'licenses';lic.mkdir(exist_ok=True)
for p in (R/'plugins').glob('*.txt'):shutil.copy2(p,lic/p.name)
shutil.copy2(R.parent/'samples/SalamanderGrandPiano/README.md',lic/'Salamander_README.md')
shutil.copy2(R.parent/'samples/VSCO-2-CE/LICENSE',lic/'VSCO_CC0.txt')
(P/'requirements.txt').write_text('numpy\nscipy\nsoundfile\nimageio-ffmpeg\n',encoding='utf-8')
(P/'run.ps1').write_text('''$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m pip install -r requirements.txt
New-Item -ItemType Directory -Force tools,plugins | Out-Null
if (!(Test-Path tools/python32/python.exe)) {
  Invoke-WebRequest https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-win32.zip -OutFile tools/python32.zip
  Expand-Archive tools/python32.zip tools/python32 -Force
}
foreach ($name in @('Mini_DiZi','Mini_ErHu')) {
  if (!(Test-Path ('plugins/'+$name+'.dll'))) {
    Invoke-WebRequest ('https://www.chineekong.com/free/'+$name+'.rar') -OutFile ('tools/'+$name+'.rar')
    & C:/Windows/System32/tar.exe -xf ('tools/'+$name+'.rar') -C plugins
  }
}
python arrange.py
& tools/python32/python.exe vst_host.py plugins/Mini_DiZi.dll dizi_xiao_plan.json dizi_xiao.wav
& tools/python32/python.exe vst_host.py plugins/Mini_ErHu.dll erhu_plan.json erhu.wav
python render_mix.py
''',encoding='utf-8')
text='''# One Last Kiss · 国风器乐版

基于上一版五页谱转录，保留 120 小节、旋律与和声结构。约 4 分 30 秒，无人声。
原作曲：Hikaru Utada；原钢琴谱改编：Animenz。

## 本版变化

- 主旋律改由笛子、箫和二胡分段接力。
- 古筝负责切分、分解和弦、快速音型及轻轮奏；使用 50 段从真实古筝录音切出的稳定单音，交替调用以减少机械重复。
- 锣、木质打击和低鼓承担推进，撤下西式军鼓、竖琴、低音提琴及西式弦乐铺底。
- 钢琴缩减到 163 个低音和弱和声音符，整体均方根电平约比古筝低 17 dB，仅承担底部支撑。
- 二胡高音段与部分笛箫段按整句调整八度；不强制改成五声音阶，不改动原和声的音级。

## 交付

One_Last_Kiss_Guofeng.mp3：完整试听，320 kbps。
One_Last_Kiss_Guofeng.wav：48 kHz / 24-bit 立体声。
stems/：五条 24-bit FLAC 分轨，对齐同一起点。
Guofeng_Arrangement.mid：分轨音符、时值与力度；普通 GM 播放器不会还原最终民族乐器音色。
Python_Project/：Python 编曲、渲染脚本和可再分发的素材。

## 复现

Windows 上安装 Python 3.12+，在项目目录运行 run.ps1。
脚本将从 Python 官网下载便携 32 位解释器，并从 Kong Audio 官网获取免费采样插件，随后渲染到 renders/。
Kong Audio 插件只允许用来创作音乐，不能再分发或制作单音采样库，因此本工程不打包其 DLL。附带其原始许可文本。最终分轨是本曲的音乐演奏轨，不是按键音色库。
已有本机插件时可放入 plugins/，脚本会直接复用。

## 来源

- 笛子、箫、二胡：Kong Audio Mini DiZi / Mini ErHu，官方免费采样插件。
  https://www.chineekong.com/free.htm
- 古筝：Pufermufin, “LOVELY CHINESE GUZHENG PLUCKED.wav”，CC0。使用公开高质量 MP3 录音的前七分钟，按起音、稳定音高与时长筛选，50 个录音切片，经校音、重采样、包络及力度处理；不是新录制的多力度专业采样库。
  https://freesound.org/people/Pufermufin/sounds/396868/
- 锣与木质打击：VCSL，Versilian Studios / Sam Gossner，CC0。
  https://github.com/sgossner/VCSL
- 低鼓：VSCO 2 Community Edition，CC0。
  https://github.com/sgossner/VSCO-2-CE
- 钢琴：Salamander Grand Piano，Alexander Holm，CC BY 3.0。
  https://github.com/sfzinstruments/SalamanderGrandPiano

## 已验证与待确认

已完成全曲渲染、全部笛箫与二胡计划音符的发声检查、完整 WAV/MP3 解码与峰值/响度检查。
数字削波为 0，实际测量与分轨电平见 render_report.json。
免费音源不具备完整商业库的逐间隔真连奏；本版利用原采样奏法、气口、运弓时长、力度和音符衔接进行处理。
仍沿用上一版图片乐谱的转录数据，尚未人工逐音认证；民族器乐的音色、呼吸和混音也尚待用户试听验收。程序检查不等于人工听感通过。
'''
(O/'制作说明.md').write_text(text,encoding='utf-8');(P/'README.md').write_text(text,encoding='utf-8');shutil.copy2(O/'render_report.json',P/'render_report.json')
with zipfile.ZipFile(O/'Guofeng_Stems.zip','w',zipfile.ZIP_STORED) as z:
 for p in (O/'stems').glob('*.flac'):z.write(p,p.name)
with zipfile.ZipFile(O/'Guofeng_Python_Project.zip','w',zipfile.ZIP_DEFLATED,compresslevel=2) as z:
 for p in P.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(P))
ff=imageio_ffmpeg.get_ffmpeg_exe();subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-ss','39','-i',str(O/'One_Last_Kiss_Guofeng.wav'),'-t','55','-af','afade=t=in:d=0.7,afade=t=out:st=52:d=3','-c:a','libmp3lame','-b:a','320k',str(O/'Guofeng_55s_Preview.mp3')],check=True)
print('PACKED',report['integrated_lufs'],report['true_peak_dbtp'],'piano below guzheng',report['piano_rms_db_below_guzheng'],flush=True)
