from pathlib import Path
import json,shutil,zipfile,struct,math,subprocess
import numpy as np,soundfile as sf,imageio_ffmpeg
ROOT=Path(__file__).resolve().parent; OUT=ROOT.parent/'outputs';PROJECT=OUT/'Python_Project';PROJECT.mkdir(exist_ok=True)
report=json.loads((OUT/'render_report.json').read_text())
master=OUT/'One_Last_Kiss_Acoustic_Remix.wav'
x,sr=sf.read(master,dtype='float32')
peak=float(np.max(abs(x)));rms=float(np.sqrt(np.mean(x*x)));tail=float(np.max(abs(x[-sr:])))
assert np.all(np.isfinite(x)) and peak<1 and tail<.002
report['audio_checks']=dict(peak_dbfs=round(20*math.log10(peak),3),rms_dbfs=round(20*math.log10(rms),3),duration_seconds=len(x)/sr,last_second_peak=tail,finite=True,clipped_samples=int(np.count_nonzero(abs(x)>=1)))
ff=imageio_ffmpeg.get_ffmpeg_exe()
r=subprocess.run([ff,'-hide_banner','-i',str(master),'-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
txt=r.stderr[r.stderr.rfind('{'):];report['loudness_check']=json.JSONDecoder().raw_decode(txt)[0]
(OUT/'render_report.json').write_text(json.dumps(report,indent=2))
# Export balanced lossless stems without over-range PCM, same headroom for all.
balance={'01_piano':1.,'02_double_bass':7.,'03_bowed_strings':14.,'04_harp':8.,'05_acoustic_percussion':4.}
for p in sorted((OUT/'stems').glob('*.wav')):
 a,rs=sf.read(p,dtype='float32');a*=balance[p.stem]*.65
 assert float(np.max(abs(a)))<1
 sf.write(p.with_suffix('.flac'),a,rs,subtype='PCM_24')
# Standalone piano MIDI with sampled-performance timing, velocity and CC64.
data=json.loads((ROOT/'score_events.json').read_text());ev=data['events']
barbeat={b:next(e['beat']-e['t'] for e in ev if e['bar']==b) for b in range(1,121)}
grid=np.arange(0,data['beats']+20,.03125);tempo=np.full(len(grid),112.)
for b in range(1,121):
 mask=(grid>=barbeat[b])&(grid<barbeat[b]+(2 if b==10 else 4))
 if b<=10:tempo[mask]=110
 if b in [9,10,18,26,34,46,54,62,70,78,86,102,110]:tempo[mask]*=np.linspace(1,.96,mask.sum())
 if b>=111:tempo[mask]=np.interp(b,[111,115,118,119,120],[105,101,96,86,69])
tempo[grid>=barbeat[120]+2]=60
seconds=np.r_[0,np.cumsum(60/tempo[:-1]*np.diff(grid))]
def tick(q):return int(np.interp(q,grid,seconds)*960*2)
def vlq(n):
 b=[n&127];n>>=7
 while n:b.insert(0,128|(n&127));n>>=7
 return bytes(b)
# Keep the renderer's expressive note on/off/velocity track, add CC64 separately.
orig=(OUT/'Piano_Performance.mid').read_bytes();division=struct.unpack('>H',orig[12:14])[0]
# Piano MIDI export is fixed at 112 BPM; tick conversion uses that grid.
def ptick(q):return int(np.interp(q,grid,seconds)*division*112/60)
ped=[]
for b in range(1,121):
 for half in [0,2]:
  if b==10 and half==2:continue
  q=barbeat[b]+half
  ped.extend([(max(0,ptick(q)-10),bytes([0xB0,64,0])),(ptick(q)+13,bytes([0xB0,64,62 if 55<=b<=102 else 88]))])
ped.append((ptick(data['beats'])+1,bytes([0xB0,64,0])))
ped.sort(key=lambda z:z[0]);track=b'\x00\xff\x03\x0bPiano pedal';last=0
for t,msg in ped:track+=vlq(t-last)+msg;last=t
track+=b'\x00\xff\x2f\x00'
fmt,ntracks,div=struct.unpack('>HHH',orig[8:14]);new=b'MThd'+struct.pack('>IHHH',6,1,ntracks+1,div)+orig[14:]+b'MTrk'+struct.pack('>I',len(track))+track
(OUT/'Piano_Performance.mid').write_bytes(new)
# Project includes every downloaded sample, licenses and recognition source.
for name in ['render_music.py','prepare_score.py','download_samples.py','score_events.json','sample_manifest.json','SalamanderGrandPiano.json','VSCO-2-CE.json']:
 shutil.copy2(ROOT/name,PROJECT/name)
shutil.copytree(ROOT/'samples',PROJECT/'samples',dirs_exist_ok=True)
(PROJECT/'omr').mkdir(exist_ok=True);shutil.copy2(ROOT/'omr/score.mxl',PROJECT/'omr/original_OMR_unreviewed.mxl')
# prepare_score expects the original name.
shutil.copy2(ROOT/'omr/score.mxl',PROJECT/'omr/score.mxl')
(PROJECT/'requirements.txt').write_text('numpy\nscipy\nsoundfile\nmusic21\nimageio-ffmpeg\npillow\n',encoding='utf-8')
readme='''# One Last Kiss · Acoustic Remix

根据用户提供的五页 Animenz 钢琴谱制作的无主唱器乐初版。
原作曲：Hikaru Utada。原钢琴改编：Animenz。

## 成品

- 约 4 分 30 秒；原谱主速度 112 BPM，段落收束和尾声有轻微速度处理。
- WAV：48 kHz / 24-bit / 立体声；MP3：320 kbps。
- 五条 FLAC 分轨：钢琴、拨弦低音提琴、弓弦、竖琴、原声打击乐。
- Piano_Performance.mid：可编辑钢琴音符、力度与踏板控制。

## 已确认的制作约束

保留原谱 120 小节与 A–O 段落顺序，原调五个升号；第 10 小节为 2/4。
声源全部来自乐器录音，不使用振荡器合成的旋律、电子贝斯或合成器铺底。
钢琴使用四档实录力度层交叉渐变；低音提琴和鼓采用多个录音版本。
同音延音线合并，连奏、重音、短断奏分别处理；半踏板按和声与密度换踏。
伴奏取自原谱和声，未加入新主旋律。整体形成安静开场、律动推进、弦乐高潮、钢琴尾声。

## 复现

Python 3.12 或更新版本：

```powershell
python -m pip install -r requirements.txt
python render_music.py
```

结果写入 renders/。score_events.json 是实际渲染的校正谱面数据，可直接编辑音高、拍点、时值和延音线。
prepare_score.py 保留从初始 OMR 到校正事件的过程；omr/original_OMR_unreviewed.mxl 是未经校正的识别中间文件，不是最终可信谱。
sample_manifest.json 记录 351 个下载条目；其中 348 个为音频文件，其余为说明与许可证。
download_samples.py 可重新下载同一公开采样集合。

## 音源与工具来源

- Salamander Grand Piano v3，Alexander Holm，CC BY 3.0。四档录音力度层 v3/v7/v11/v15；本版以重采样、力度交叉渐变及包络处理。
  https://github.com/sfzinstruments/SalamanderGrandPiano
  https://creativecommons.org/licenses/by/3.0/
- VSCO 2 Community Edition，Versilian Studios / Sam Gossner，CC0。乐器实际音区经频谱检查，修正了文件名与科学音高记法的八度差别。
  https://github.com/sgossner/VSCO-2-CE
- Audiveris：图片乐谱识别，仅作为转录起点。
  https://github.com/Audiveris/audiveris

各音源原始许可证与说明保存在 samples/ 内。

## 验证范围与待确认项

已完成：五页排序、120 小节结构核对、478 拍统一时间轴、常见识别节奏错误校正、J 段八度线处理、同音延音合并、采样根音抽查、全曲离线渲染、响度与数字峰值检查、完整文件解码。
已调整 124 个手部/小节的转录或节奏数据；这表示校正工作量，不代表其他小节已经逐音认证。
本版实际使用的采样文件数量与成品检测数值见 render_report.json。

待确认：未进行人工逐音听写复核及用户试听验收。图片中的密集和弦、跨声部连线及部分尾声和弦仍可能存在转录误差；不能保证与原谱每个音符完全一致。
节奏配器、弦乐进入方式与空间混响属于本次 remix 的制作选择，尚待用户确认。
'''
(OUT/'制作说明.md').write_text(readme,encoding='utf-8');(PROJECT/'README.md').write_text(readme,encoding='utf-8')
shutil.copy2(OUT/'render_report.json',PROJECT/'render_report.json')
with zipfile.ZipFile(OUT/'One_Last_Kiss_Python_Project.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=2) as z:
 for p in PROJECT.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(PROJECT))
with zipfile.ZipFile(OUT/'One_Last_Kiss_Stems.zip','w',compression=zipfile.ZIP_STORED) as z:
 for p in (OUT/'stems').glob('*.flac'):z.write(p,p.name)
print(json.dumps(report['audio_checks']),flush=True)
print(json.dumps(report['loudness_check']),flush=True)
print('PACKAGING DONE',flush=True)
