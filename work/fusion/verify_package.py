from pathlib import Path
import json,math,zipfile,shutil,struct,subprocess,sys
import numpy as np,soundfile as sf
from scipy import signal
import imageio_ffmpeg
R=Path(__file__).resolve().parent;W=R.parent;O=W.parent/'outputs/Fusion';P=O/'Python_Project';P.mkdir(exist_ok=True)
rep=json.loads((O/'render_report.json').read_text());a=json.loads((R/'arrangement.json').read_text());ff=imageio_ffmpeg.get_ffmpeg_exe()
# Compare relative bass energy at matched score positions, independently of master loudness.
sr=48000;new,_=sf.read(O/'One_Last_Kiss_Fusion.wav',dtype='float32');first,_=sf.read(O.parent/'One_Last_Kiss_Acoustic_Remix.wav',dtype='float32');prev,_=sf.read(O.parent/'Guofeng/One_Last_Kiss_Guofeng.wav',dtype='float32')
grid=np.array(a['grid']);seconds=np.array(a['seconds']);bb={int(k):v for k,v in a['barbeat'].items()}
def nt(q):return a['intro_seconds']+float(np.interp(q,grid,seconds))
oldtempo=np.full(len(grid),112.)
for b in range(1,121):
 mask=(grid>=bb[b])&(grid<bb[b]+(2 if b==10 else 4))
 if b<=10:oldtempo[mask]=110
 if b in [9,10,18,26,34,46,54,62,70,78,86,102,110]:oldtempo[mask]*=np.linspace(1,.96,mask.sum())
 if b>=111:oldtempo[mask]=np.interp(b,[111,115,118,119,120],[105,101,96,86,69])
oldtempo[grid>=bb[120]+2]=60;oldsec=np.r_[0,np.cumsum(60/oldtempo[:-1]*np.diff(grid))]
def ot(q):return .35+float(np.interp(q,grid,oldsec))
def bassratio(x,start,end):
 x=x[round(start*sr):round(end*sr)].mean(axis=1)
 low=signal.sosfilt(signal.butter(3,[35,160],btype='bandpass',fs=sr,output='sos'),x)
 mid=signal.sosfilt(signal.butter(3,[250,2500],btype='bandpass',fs=sr,output='sos'),x)
 return float(20*np.log10(np.sqrt(np.mean(low*low))/max(1e-12,np.sqrt(np.mean(mid*mid)))))
comparison=[]
for name,start,end in [('C',19,27),('D',27,35),('G',47,55),('H',55,63),('J',71,79),('M',95,103)]:
 q=bb[start];qe=bb[end]
 comparison.append(dict(section=name,first=bassratio(first,ot(q),ot(qe)),previous_guofeng=bassratio(prev,ot(q),ot(qe)),fusion=bassratio(new,nt(q),nt(qe))))
rep['relative_bass_35_160_vs_mid_250_2500_db']=comparison
rep['median_bass_db_vs_first']=float(np.median([x['fusion']-x['first'] for x in comparison]))
rep['median_bass_db_vs_previous_guofeng']=float(np.median([x['fusion']-x['previous_guofeng'] for x in comparison]))
checks=rep['native_note_checks'];summary={}
for kind,rows in checks.items():
 missing=[r for r in rows if r['start_rms']<.00004]
 long=[r for r in rows if 'late_rms' in r]
 failed=[r for r in long if r['late_rms']<.00004]
 summary[kind]=dict(planned_notes=len(rows),missing_attack_count=len(missing),long_notes=len(long),silent_late_count=len(failed),missing=missing,silent_late=failed)
rep['native_summary']=summary
if '--analysis-only' in sys.argv:
 print('BASS',json.dumps(comparison),rep['median_bass_db_vs_first'],rep['median_bass_db_vs_previous_guofeng'],flush=True)
 print('NATIVE',json.dumps(summary),flush=True)
 sys.exit(0)
assert not any(r['missing_attack_count'] or r['silent_late_count'] for r in summary.values()),summary
assert rep['clipped_samples']==0 and rep['tail_peak_last_second']<.0001
rep['stereo_mono_correlation']=float(np.corrcoef(new[::40,0],new[::40,1])[0,1])
decode=subprocess.run([ff,'-hide_banner','-loglevel','error','-i',str(O/'One_Last_Kiss_Fusion.mp3'),'-f','null','-'],capture_output=True)
assert decode.returncode==0
rep['mp3_decode_ok']=True
(O/'render_report.json').write_text(json.dumps(rep,indent=2))
print('QA',json.dumps(summary),flush=True);print('BASS',rep['median_bass_db_vs_first'],rep['median_bass_db_vs_previous_guofeng'],flush=True)
# Opening demonstrates the new prelude; chorus clip demonstrates thickened lead and bass.
for name,start,dur in [('Opening_45s',0,45),('Chorus_55s',nt(bb[19])-.8,55)]:
 subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-ss',str(start),'-i',str(O/'One_Last_Kiss_Fusion.wav'),'-t',str(dur),'-af',f'afade=t=in:d=0.1,afade=t=out:st={dur-2}:d=2','-c:a','libmp3lame','-b:a','320k',str(O/(name+'.mp3'))],check=True)
# Editable performance MIDI uses absolute seconds translated to a fixed 120 BPM grid.
def vlq(x):
 b=[x&127];x>>=7
 while x:b.insert(0,(x&127)|128);x>>=7
 return bytes(b)
def track(label,events):
 label=label.encode();s=b'\0\xff\x03'+vlq(len(label))+label;last=0
 for t,msg in sorted(events,key=lambda x:(x[0],x[1][0]&0xf0)):
  tick=max(0,round(t*1920));s+=vlq(tick-last)+msg;last=tick
 s+=b'\0\xff\x2f\0';return b'MTrk'+struct.pack('>I',len(s))+s
tracks=[track('Tempo',[(0,b'\xff\x51\x03\x07\xa1\x20')])]
for ch,kind in enumerate(['wind','erhu','guzheng','violins','cello','bass','piano']):
 ev=[]
 for n in a[kind]:ev.extend([(n['on'],bytes([0x90+ch,n['p'],int(np.clip(n['v'],1,127))])),(n['off'],bytes([0x80+ch,n['p'],0]))])
 tracks.append(track(kind,ev))
(O/'Fusion_Arrangement.mid').write_bytes(b'MThd'+struct.pack('>IHHH',6,1,len(tracks),960)+b''.join(tracks))
for f in ['arrange_fusion.py','render_fusion.py','vst_host.py','arrangement.json','native_plans.json']:
 shutil.copy2(R/f,P/f)
for f in R.glob('wind_*.json'):shutil.copy2(f,P/f.name)
for f in R.glob('erhu_*.json'):
 if 'probe' not in f.name:shutil.copy2(f,P/f.name)
shutil.copy2(W/'score_events.json',P/'score_events.json')
old=json.loads((W/'guofeng/arrangement.json').read_text());(P/'previous_melody.json').write_text(json.dumps(dict(melody=old['melody']),indent=2))
shutil.copy2(W/'guofeng/guzheng_manifest.json',P/'guzheng_manifest.json')
for original,relative in rep['used_samples'].items():
 dest=P/'samples'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,dest)
lic=P/'licenses';lic.mkdir(exist_ok=True)
for f in (W/'guofeng/plugins').glob('*.txt'):shutil.copy2(f,lic/f.name)
shutil.copy2(W/'samples/SalamanderGrandPiano/README.md',lic/'Salamander_README.md')
shutil.copy2(W/'samples/VSCO-2-CE/LICENSE',lic/'VSCO_CC0.txt')
shutil.copy2(O/'render_report.json',P/'render_report.json')
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
python arrange_fusion.py
$plans=Get-Content native_plans.json -Raw | ConvertFrom-Json
foreach($plan in $plans) {
 $dll=if($plan.kind -eq 'wind'){'plugins/Mini_DiZi.dll'}else{'plugins/Mini_ErHu.dll'}
 & tools/python32/python.exe vst_host.py $dll ($plan.name+'.json') ($plan.name+'.wav')
}
python render_fusion.py
''',encoding='utf-8')
readme=f'''# One Last Kiss · 中西合璧器乐版

原作曲 Hikaru Utada；主题钢琴谱改编 Animenz；本版以用户提供的五页谱与前版转录为主题依据。

## 编排

时长 {rep['duration_seconds']:.2f} 秒，约 4 分 54 秒。
新增 {rep['intro_seconds']:.2f} 秒、八小节渐入引子：C#m9 / Emaj9 / F#6 / D#m7 的两轮展开，引用原主题的短句，随后回到原谱 A 段。
正文保留原谱 A–O 顺序；笛箫和二胡分句交接，古筝承担弹拨律动，西洋小提琴群与大提琴增加主旋律的中频厚度。
低音提琴、大提琴和钢琴低区共同支撑低音；钢琴最高只参与中低区和声，不接管主题领奏。
低鼓、锣、木质打击与少量原声鼓填充提供节奏推进，无电子合成器声部。

## 对上版反馈的修改

1. 延音线先逐音合并再分配乐器；古筝保留原录音衰减，不再按短音统一截断。
2. 修复同音连奏的旧松键关掉新音的问题；不同奏法各自渲染，避免切换预置截断尾音。
3. 笛子与二胡重新设置保持/松键包络，长音后段保持发声；换气放在分句末端，弦乐承接主题的持续线条。
4. 恢复真实弦乐与低音提琴；保留钢琴最低 C#1 等低音，补足低频基础。
5. 新增共享的扩散房间尾响；终止和弦有延长，之后预留自然衰减时间。

## 文件

One_Last_Kiss_Fusion.wav：48 kHz / 24-bit 立体声。
One_Last_Kiss_Fusion.mp3：320 kbps。
Opening_45s.mp3：新引子与主题进入；Chorus_55s.mp3：合奏与低音段。
stems/：八条对齐的 FLAC 分轨；Fusion_Arrangement.mid：七条可编辑音符轨，普通 GM 音色不能还原成品。
Python_Project/：编曲、渲染脚本、事件与可再分发采样。Windows Python 3.12+ 下运行 run.ps1 可复现。

Kong Audio 插件本体不可再分发，因此工程不打包 DLL；run.ps1 从官方下载，或复用 plugins/ 内已有文件。

## 检查

成品综合响度 {rep['integrated_lufs']:.2f} LUFS，真峰值 {rep['true_peak_dbtp']:.2f} dBTP，数字削波为零。
对计划中的每个笛箫/二胡音检查起音，并检查长音的后 72%–92% 区间；详细结果见 render_report.json。
检查了完整版 MP3 解码、尾部衰减、立体声与单声道相关性。
在 C/D/G/H/J/M 的同谱面区间，比较了 35–160 Hz 与 250–2500 Hz 能量比例。相对第一版中位差 {rep['median_bass_db_vs_first']:+.2f} dB，相对上一国风版 {rep['median_bass_db_vs_previous_guofeng']:+.2f} dB。这是频段指标，不代表人工听感评分。
尚未完成人工逐音审谱和用户试听验收；本版真实采样与数字衔接不等于现场演奏或完整商业真连奏库。

## 参考与来源

- Animenz 官方五页谱条目（用于确认版本）：https://www.mymusic5.com/animenzzz/46382
- FAIRY 十五页乐队总谱的出版信息，原调 B，含键盘、低音、打击乐与鼓。完整谱为付费商品，本次未购买或使用其完整谱面：
  https://www.print-gakufu.com/score/detail/494707/
- 笛箫与二胡：Kong Audio Mini DiZi / Mini ErHu 官方免费采样插件，许可限用于音乐创作，不再分发插件或制作单音采样库。
  https://www.chineekong.com/free.htm
- 古筝：Pufermufin “LOVELY CHINESE GUZHENG PLUCKED.wav”，CC0，从公开录音筛选 50 段稳定单音，校音、交替调用、保留自然尾音。
  https://freesound.org/people/Pufermufin/sounds/396868/
- 小提琴群、大提琴、拨弦低音提琴与低鼓：VSCO 2 Community Edition，Versilian Studios / Sam Gossner，CC0。
  https://github.com/sgossner/VSCO-2-CE
- 锣和木质打击：VCSL，CC0。https://github.com/sgossner/VCSL
- 钢琴：Alexander Holm，Salamander Grand Piano v3，CC BY 3.0。https://github.com/sfzinstruments/SalamanderGrandPiano
'''
(O/'制作与检查说明.md').write_text(readme,encoding='utf-8');(P/'README.md').write_text(readme,encoding='utf-8')
with zipfile.ZipFile(O/'Fusion_Stems.zip','w',zipfile.ZIP_STORED) as z:
 for p in (O/'stems').glob('*.flac'):z.write(p,p.name)
with zipfile.ZipFile(O/'Fusion_Python_Project.zip','w',zipfile.ZIP_DEFLATED,compresslevel=2) as z:
 for p in P.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(P))
print('PACKAGED',flush=True)
