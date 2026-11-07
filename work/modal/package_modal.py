from pathlib import Path
import json,shutil,zipfile,subprocess,struct,math
import numpy as np,soundfile as sf
from scipy import signal
import imageio_ffmpeg
R=Path(__file__).resolve().parent;W=R.parent;O=W.parent/'outputs/Modal';P=O/'Python_Project';P.mkdir(parents=True,exist_ok=True)
a=json.loads((R/'arrangement.json').read_text());report=json.loads((O/'render_report.json').read_text());ff=imageio_ffmpeg.get_ffmpeg_exe()
parts=['suona','xiao','sax','oboe','erhu','guzheng','violins','cello','bass','piano'];allowed={1,4,6,8,11}
pitch_audit={k:dict(notes=len(a[k]),pitch_classes=sorted({n['p']%12 for n in a[k]}),out_of_mode=sum(n['p']%12 not in allowed for n in a[k])) for k in parts}
assert all(x['out_of_mode']==0 for x in pitch_audit.values())
summary={}
for k,rows in report['native_note_checks'].items():
 summary[k]=dict(notes=len(rows),silent_attack=sum(n['start_rms']<.00004 for n in rows),long_notes=sum('late_rms' in n for n in rows),silent_late=sum(n.get('late_rms',1)<.00004 for n in rows))
assert not any(x['silent_attack'] or x['silent_late'] for x in summary.values()),summary
assert report['clipped_samples']==0 and report['tail_peak_last_second']<.0001
report['pitch_class_audit']=pitch_audit;report['performance_audit']=summary
grid=np.array(a['grid']);seconds=np.array(a['seconds']);bb={int(k):v for k,v in a['barbeat'].items()}
def tm(q):return a['intro_seconds']+float(np.interp(q,grid,seconds))
# A matched xiao-register comparison, not an unsupported subjective harshness rating.
prev,psr=sf.read(O.parent/'Fusion/stems/01_dizi_xiao.flac',dtype='float32');now,nsr=sf.read(O/'stems/02_xiao.flac',dtype='float32')
def colour(x,sr):
 x=x[round(tm(bb[79])*sr):round(tm(bb[87])*sr)].mean(axis=1)
 high=signal.sosfilt(signal.butter(3,[2500,7000],fs=sr,btype='bandpass',output='sos'),x)
 body=signal.sosfilt(signal.butter(3,[300,2000],fs=sr,btype='bandpass',output='sos'),x)
 return float(20*np.log10(np.sqrt(np.mean(high*high))/max(1e-12,np.sqrt(np.mean(body*body)))))
report['xiao_high_band_ratio_db']=dict(previous=colour(prev,psr),new=colour(now,nsr),bands='2500-7000 Hz / 300-2000 Hz, K section; notes differ after adaptation')
r=subprocess.run([ff,'-hide_banner','-loglevel','error','-i',str(O/'One_Last_Kiss_Yu_Mode.mp3'),'-f','null','-'],capture_output=True);assert r.returncode==0
report['mp3_decode_ok']=True
(O/'render_report.json').write_text(json.dumps(report,indent=2))
for name,start,duration in [('Reeds_70s_Preview',tm(bb[19])-.7,70),('Xiao_25s_Preview',tm(bb[79])-.5,25)]:
 subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-ss',str(start),'-i',str(O/'One_Last_Kiss_Yu_Mode.wav'),'-t',str(duration),'-af',f'afade=t=in:d=0.2,afade=t=out:st={duration-2}:d=2','-c:a','libmp3lame','-b:a','320k',str(O/(name+'.mp3'))],check=True)
def vlq(n):
 b=[n&127];n>>=7
 while n:b.insert(0,128|(n&127));n>>=7
 return bytes(b)
def track(label,events):
 label=label.encode();data=b'\0\xff\x03'+vlq(len(label))+label;last=0
 for t,msg in sorted(events,key=lambda e:(e[0],e[1][0]&0xf0)):
  tick=max(0,round(t*1920));data+=vlq(tick-last)+msg;last=tick
 data+=b'\0\xff\x2f\0';return b'MTrk'+struct.pack('>I',len(data))+data
tracks=[track('Tempo',[(0,b'\xff\x51\x03\x07\xa1\x20')])]
programs=[111,73,66,68,110,107,48,42,43,0];channels=list(range(9))+[10]
for k,ch,pr in zip(parts,channels,programs):
 ev=[(0,bytes([0xc0+ch,pr]))]
 for n in a[k]:ev.extend([(n['on'],bytes([0x90+ch,n['p'],round(max(1,min(127,n['v'])))])),(n['off'],bytes([0x80+ch,n['p'],0]))])
 tracks.append(track(k,ev))
ev=[]
for n in a['percussion']:
 p={'lowdrum':35,'wood':76,'gong':52,'frame':38}[n['kind']];v=round(np.clip(n['gain']*100,15,110));ev.extend([(n['on'],bytes([0x99,p,v])),(n['on']+.15,bytes([0x89,p,0]))])
tracks.append(track('Acoustic percussion',ev))
(O/'Yu_Mode_FL_Import.mid').write_bytes(b'MThd'+struct.pack('>IHHH',6,1,len(tracks),960)+b''.join(tracks))
# Ready-to-run editable source. Licensed FL assets and Kong DLLs are not redistributed.
for f in ['arrange_modal.py','render_modal.py','reed_performances.py','arrangement.json','suona_manifest.json','xiao_plan.json','erhu_plan.json','wind_manifest.json']:
 shutil.copy2(R/f,P/f)
shutil.copy2(W/'fusion/vst_host.py',P/'vst_host.py')
shutil.copy2(W/'fusion/arrangement.json',P/'foundation.json')
mel=json.loads((W/'guofeng/arrangement.json').read_text());(P/'source_melody.json').write_text(json.dumps(dict(melody=mel['melody']),indent=2))
shutil.copy2(W/'guofeng/guzheng_manifest.json',P/'guzheng_manifest.json')
for original,relative in report['used_samples'].items():
 dest=P/'samples'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,dest)
for kind in ['suona','oboe','sax']:
 shutil.copytree(R/'samples'/kind,P/'samples'/kind,dirs_exist_ok=True)
shutil.copytree(W/'guofeng/samples/guzheng',P/'samples/guzheng',dirs_exist_ok=True)
lic=P/'licenses';lic.mkdir(exist_ok=True)
for p in (W/'guofeng/plugins').glob('*.txt'):shutil.copy2(p,lic/p.name)
shutil.copy2(W/'samples/SalamanderGrandPiano/README.md',lic/'Salamander_README.md');shutil.copy2(W/'samples/VSCO-2-CE/LICENSE',lic/'VSCO_CC0.txt')
(lic/'Suona_sources.md').write_text('''# Suona recording sources and adaptations

1. “Suona.ogg”, Francesc Fort / TaronjaSatsuma, NENU Folklorical Orchestra, own recording, 2023-11-28.
Source: https://commons.wikimedia.org/wiki/File:Suona.ogg
License: Creative Commons Attribution-ShareAlike 4.0, https://creativecommons.org/licenses/by-sa/4.0/
Changes: selected stable single-tone regions, trimmed, normalized, retuned, resampled, crossfaded for sustain, envelopes and equalization. The adapted sample slices retain CC BY-SA 4.0. Corresponding suona performance is an adaptation, not an original new recording.

2. “suona.wav”, jiemojiemo, Freesound, CC0.
Source: https://freesound.org/people/jiemojiemo/sounds/514114/
License: https://creativecommons.org/publicdomain/zero/1.0/
Changes: extracted sustained recorded tone, retuned and shaped for performance.

This document describes the recording licenses. The composition One Last Kiss and its piano arrangement retain their respective authorship and copyrights; no CC0 claim is made about the composition.
''',encoding='utf-8')
(P/'requirements.txt').write_text('numpy\nscipy\nsoundfile\nimageio-ffmpeg\n',encoding='utf-8')
(P/'run.ps1').write_text('''$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m pip install -r requirements.txt
New-Item -ItemType Directory -Force tools,plugins | Out-Null
if (!(Test-Path tools/python32/python.exe)) {
 Invoke-WebRequest https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-win32.zip -OutFile tools/python32.zip
 Expand-Archive tools/python32.zip tools/python32 -Force
}
foreach($name in @('Mini_DiZi','Mini_ErHu')) {
 if (!(Test-Path ('plugins/'+$name+'.dll'))) {
  Invoke-WebRequest ('https://www.chineekong.com/free/'+$name+'.rar') -OutFile ('tools/'+$name+'.rar')
  & C:/Windows/System32/tar.exe -xf ('tools/'+$name+'.rar') -C plugins
 }
}
python arrange_modal.py
& tools/python32/python.exe vst_host.py plugins/Mini_DiZi.dll xiao_plan.json xiao.wav
& tools/python32/python.exe vst_host.py plugins/Mini_ErHu.dll erhu_plan.json erhu.wav
python render_modal.py
''',encoding='utf-8')
local='''# FL Studio 本地素材检索

检查范围：用户提供的 本地 FL Studio 素材目录。

找到与本任务相关的文件：

|文件|用途与结论|
|---|---|
|Data/Patches/Packs/Legacy/Instruments/Orchestral/FLS Tenor Sax.dwp|DirectWave 次中音萨克斯预置，可用于 FL 内演奏；本版选择多奏法、多录音变体的 VCSL 萨克斯。|
|Data/System/FL Mobile/Instruments/Alto Sax 01.ini|内含 ALTSAX 单音采样映射、音高与保持参数；是音源配置，不是演奏 MIDI。|
|Data/System/MIDI import/069 Oboe.fst|GM 双簧管导入预置；本版使用 VSCO 2 CE 实录双簧管。|
|Data/System/MIDI import/067 Tenor Sax.fst|GM 次中音萨克斯导入预置。|
|Data/Patches/Plugin presets/Generators/Kepler Exo/X Sako/Instrument/Brass and Winds/Suona.fst|Kepler Exo 合成器预置；本次没有将其当作真实唢呐采样。|
|Data/Patches/Scores/FPC drumloops/|大量 MIDI 为鼓组节奏循环，不会提供唢呐的实际音色。|

未复制或修改 FL 安装目录与用户预置。交付的 MIDI 可导入 FL；默认 GM 音色仅供识别声部，准确成品以 WAV/MP3 与分轨为准。
'''
(O/'FL素材检索.md').write_text(local,encoding='utf-8')
readme=f'''# One Last Kiss · 羽调式管乐合奏版

时长 {report['duration_seconds']:.2f} 秒，保留上一版约 20.6 秒引子、120 小节结构、节奏铺底与低音层次。
原作曲 Hikaru Utada；主题依据用户提供的 Animenz 五页钢琴谱及此前转录。

## 当前确认的编排

- 主体为唢呐、箫、次中音萨克斯、双簧管的分段接力和呼应。
- 二胡仅作单线长弓铺底，电平降低，不再承担主题领奏。
- 古筝、钢琴、低音提琴、大提琴和西洋弦乐延续前版的节奏与厚度。
- 十个有音高声部统一为 E 宫系统下的 C# 羽五声框架：C#、E、F#、G#、B。按旋律走向选择邻音，并改写低音走向和和声；原曲的节奏动机和段落骨架保留，不再声称逐音照搬原谱。
- 箫使用独立的真实箫采样预置与低区呼应线；不再把高区笛子统称为箫。箫作 2.7 kHz 约 -5 dB 的宽带处理，并缓降 3.8 kHz 以上，放缓起音。
- 连续管乐短音只保留很短的干声交叠，房间混响承接尾音；换气点留在分句末端。

## 音源与表现力的实际范围

萨克斯使用 VCSL 次中音萨克斯的实录非颤音、颤音与短音；双簧管使用 VSCO 2 CE 的持续、颤音、短音与多个录音版本。其音高映射已经抽查，文件名八度与科学音高之间的差异已校正。
唢呐采用公开真实演奏录音中的稳定单音重采样，保留录音本身的气震和音色；较长音用内段交叉渐变延长。它不是完整的专业多力度、逐间隔真连奏商业音源，不能据此声称达到现场唢呐演奏的全部表现力。
本地 FL 安装中找到了萨克斯和双簧管相关预置；检索到的 Suona.fst 是合成器预置，本版没有使用。详见 FL素材检索.md。

## 文件与复现

One_Last_Kiss_Yu_Mode.wav：48 kHz / 24-bit 立体声；MP3：320 kbps。
Reeds_70s_Preview.mp3：唢呐、萨克斯、双簧管与箫呼应；Xiao_25s_Preview.mp3：低区箫段。
Yu_Mode_FL_Import.mid：十条旋律/和声轨与一条打击乐轨，可导入 FL Studio。GM 预置只作通用回放，不会还原最终民族音色。
stems/：十一条 FLAC 分轨，对齐同一起点。
Python_Project/：编曲事件、脚本和可再分发的采样；Windows Python 3.12+ 下运行 run.ps1。
Kong Audio DLL 不可再分发，因此 run.ps1 从官网下载，或复用 plugins/ 内已有插件；未打包 FL 的商业预置。

## 检查与待确认

十个有音高声部的事件均通过五声音高集合检查。唢呐 {summary['suona']['notes']}、箫 {summary['xiao']['notes']}、萨克斯 {summary['sax']['notes']}、双簧管 {summary['oboe']['notes']}、二胡 {summary['erhu']['notes']} 个计划音符均检测到起音；长音后段没有静音。
实际综合响度 {report['integrated_lufs']:.2f} LUFS，真峰值 {report['true_peak_dbtp']:.2f} dBTP，数字削波为零；完整版 MP3 可完整解码。
箫 K 段高频/中频能量比例的前后变化见 render_report.json；改编后音符也不同，此指标不是主观听感评分。
这些是离线结构和信号检查；尚未完成人工逐音听审或用户试听验收。

## 来源

- VCSL / Versilian Studios / Sam Gossner，CC0（萨克斯、锣、木质打击）：https://github.com/sgossner/VCSL
- VSCO 2 Community Edition，CC0（双簧管、弦乐、低音提琴、鼓）：https://github.com/sgossner/VSCO-2-CE
- Kong Audio Mini DiZi 的 Xiao 预置及 Mini ErHu：https://www.chineekong.com/free.htm
- 唢呐：Francesc Fort / TaronjaSatsuma，NENU Folklorical Orchestra 实录，CC BY-SA 4.0：https://commons.wikimedia.org/wiki/File:Suona.ogg
  另含 jiemojiemo 的 CC0 持续音：https://freesound.org/people/jiemojiemo/sounds/514114/
  切片、重采样、校音、包络与尾音处理及许可记录见 licenses/Suona_sources.md。
- 古筝：Pufermufin，CC0：https://freesound.org/people/Pufermufin/sounds/396868/
- 钢琴：Alexander Holm / Salamander Grand Piano v3，CC BY 3.0：https://github.com/sfzinstruments/SalamanderGrandPiano
'''
(O/'制作与检查说明.md').write_text(readme,encoding='utf-8');(P/'README.md').write_text(readme,encoding='utf-8');shutil.copy2(O/'FL素材检索.md',P/'FL素材检索.md');shutil.copy2(O/'render_report.json',P/'render_report.json')
with zipfile.ZipFile(O/'Yu_Mode_Stems.zip','w',zipfile.ZIP_STORED) as z:
 for p in (O/'stems').glob('*.flac'):z.write(p,p.name)
with zipfile.ZipFile(O/'Yu_Mode_Python_Project.zip','w',zipfile.ZIP_DEFLATED,compresslevel=2) as z:
 for p in P.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(P))
print('MODE',json.dumps(pitch_audit),flush=True);print('PERFORMANCES',json.dumps(summary),flush=True);print('PACKAGED',flush=True)
