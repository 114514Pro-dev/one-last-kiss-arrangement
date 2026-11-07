from pathlib import Path
import json,shutil,zipfile,subprocess,struct
import numpy as np
import imageio_ffmpeg
R=Path(__file__).resolve().parent;W=R.parent;O=W.parent/'outputs/Reeds';P=O/'Python_Project';P.mkdir(parents=True,exist_ok=True)
a=json.loads((R/'arrangement.json').read_text());base=json.loads((W/'fusion/arrangement.json').read_text());rep=json.loads((O/'render_report.json').read_text());ff=imageio_ffmpeg.get_ffmpeg_exe()
restored={}
for k in ['guzheng','piano','bass','cello','violins']:
 actual=[(n['p'],n['on'],n['off']) for n in a[k]];expected=[(n['p'],n['on'],n['off']) for n in base[k]]
 restored[k]=dict(events=len(actual),pitch_and_timing_restored=actual==expected);assert actual==expected
melody_changes=[]
for k in ['suona','sax','oboe']:
 for n in a[k]:
  if 'source_pitch' in n and n['p']%12!=n['source_pitch']%12:melody_changes.append([k,n['bar'],n['p'],n['source_pitch']])
assert not melody_changes
summary={k:dict(notes=len(v),silent_attack=sum(n['start_rms']<.00004 for n in v),silent_late=sum(n.get('late_rms',1)<.00004 for n in v)) for k,v in rep['native_note_checks'].items()}
assert not any(n['silent_attack'] or n['silent_late'] for n in summary.values()),summary
assert rep['clipped_samples']==0 and rep['tail_peak_last_second']<.0001
rep['restoration_audit']=restored;rep['theme_pitch_class_substitutions']=melody_changes;rep['performance_audit']=summary
rep['pitch_classes']={k:sorted({n['p']%12 for n in a[k]}) for k in ['suona','xiao','sax','oboe','erhu','guzheng','violins','cello','bass','piano']}
cmd=[ff,'-hide_banner','-loglevel','error','-i',str(O/'One_Last_Kiss_Original_Harmony_Reeds.mp3'),'-f','null','-'];assert subprocess.run(cmd,capture_output=True).returncode==0
rep['mp3_decode_ok']=True;(O/'render_report.json').write_text(json.dumps(rep,indent=2))
q=a['barbeat']['19'];start=a['intro_seconds']+float(np.interp(q,np.array(a['grid']),np.array(a['seconds'])))-.7
subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-ss',str(start),'-i',str(O/'One_Last_Kiss_Original_Harmony_Reeds.wav'),'-t','70','-af','afade=t=in:d=0.2,afade=t=out:st=68:d=2','-c:a','libmp3lame','-b:a','320k',str(O/'Original_Harmony_70s_Preview.mp3')],check=True)
def vlq(n):
 b=[n&127];n>>=7
 while n:b.insert(0,128|(n&127));n>>=7
 return bytes(b)
def track(label,ev):
 label=label.encode();out=b'\0\xff\x03'+vlq(len(label))+label;last=0
 for t,msg in sorted(ev,key=lambda e:(e[0],e[1][0]&0xf0)):
  tick=max(0,round(t*1920));out+=vlq(tick-last)+msg;last=tick
 out+=b'\0\xff\x2f\0';return b'MTrk'+struct.pack('>I',len(out))+out
tracks=[track('Tempo',[(0,b'\xff\x51\x03\x07\xa1\x20')])]
parts=['suona','xiao','sax','oboe','erhu','guzheng','violins','cello','bass','piano']
for k,ch,pr in zip(parts,list(range(9))+[10],[111,73,66,68,110,107,48,42,43,0]):
 ev=[(0,bytes([0xc0+ch,pr]))]
 for n in a[k]:ev.extend([(n['on'],bytes([0x90+ch,n['p'],round(np.clip(n['v'],1,127))])),(n['off'],bytes([0x80+ch,n['p'],0]))])
 tracks.append(track(k,ev))
ev=[]
for n in a['percussion']:
 p={'lowdrum':35,'wood':76,'gong':52,'frame':38}[n['kind']];v=round(np.clip(n['gain']*100,15,110));ev.extend([(n['on'],bytes([0x99,p,v])),(n['on']+.15,bytes([0x89,p,0]))])
tracks.append(track('Acoustic percussion',ev));(O/'Original_Harmony_FL_Import.mid').write_bytes(b'MThd'+struct.pack('>IHHH',6,1,len(tracks),960)+b''.join(tracks))
for f in ['arrange_reeds.py','render_reeds.py','reed_performances.py','arrangement.json','suona_manifest.json','wind_manifest.json','xiao_plan.json','erhu_plan.json']:shutil.copy2(R/f,P/f)
shutil.copy2(W/'fusion/vst_host.py',P/'vst_host.py');shutil.copy2(W/'fusion/arrangement.json',P/'foundation.json')
old=json.loads((W/'guofeng/arrangement.json').read_text());(P/'source_melody.json').write_text(json.dumps(dict(melody=old['melody']),indent=2));shutil.copy2(W/'guofeng/guzheng_manifest.json',P/'guzheng_manifest.json')
for original,relative in rep['used_samples'].items():
 dest=P/'samples'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,dest)
for kind in ['suona','sax','oboe']:shutil.copytree(W/'modal/samples'/kind,P/'samples'/kind,dirs_exist_ok=True)
shutil.copytree(W/'guofeng/samples/guzheng',P/'samples/guzheng',dirs_exist_ok=True)
shutil.copytree(O.parent/'Modal/Python_Project/licenses',P/'licenses',dirs_exist_ok=True)
run=(O.parent/'Modal/Python_Project/run.ps1').read_text(encoding='utf-8').replace('arrange_modal.py','arrange_reeds.py').replace('render_modal.py','render_reeds.py');(P/'run.ps1').write_text(run,encoding='utf-8')
shutil.copy2(O.parent/'Modal/Python_Project/requirements.txt',P/'requirements.txt');shutil.copy2(O/'render_report.json',P/'render_report.json')
readme=f'''# One Last Kiss · 原和声管乐合奏版

已取消五声调式改写。恢复五声化之前谱面转录的主题音高、低音、和声与 F# 结尾；保留当前唢呐、箫、萨克斯、双簧管配器，二胡仍仅铺底。
箫仍使用真实低区 Xiao 预置，保留缓起音、2.7 kHz 降刺和高频柔化；持续音、气口与自然尾响处理继续保留。
原作曲：Hikaru Utada；主题谱面依据用户提供的 Animenz 五页谱及此前转录。约 20.6 秒引子保留，完整时长 {rep['duration_seconds']:.2f} 秒。

## 检查

钢琴、古筝、低音提琴、大提琴、西洋弦乐的全部音高与拍点均已同五声化前版本逐事件比较，相符。
正文主领奏的音高类别与源旋律一致，仅按乐器音区整体移八度；没有五声音阶量化或强制 C# 羽终止。
各领奏计划音符均有起音，长音后段无静音；成品 {rep['integrated_lufs']:.2f} LUFS / {rep['true_peak_dbtp']:.2f} dBTP，无数字削波，MP3 可完整解码。
这不等于人工逐音审谱或试听验收；仍沿用此前图片谱转录。唢呐为公开实录切片重采样，不是完整商业真连奏库。

## 使用

完整版提供 48 kHz / 24-bit WAV、320 kbps MP3、十一条 FLAC 分轨及 FL 可导入 MIDI。GM MIDI 回放不会还原成品音色。
Python_Project 内运行 run.ps1 可复现；需要 Windows Python 3.12+，脚本从官方取得便携 32 位 Python 与 Kong Audio 免费插件。本项目未打包 Kong DLL 或 FL 商业预置。

## 素材来源

萨克斯、锣和木质打击：VCSL / Versilian Studios / Sam Gossner，CC0：https://github.com/sgossner/VCSL
双簧管、弦乐、低音提琴、低鼓：VSCO 2 Community Edition，CC0：https://github.com/sgossner/VSCO-2-CE
箫与二胡：Kong Audio Mini DiZi / Mini ErHu：https://www.chineekong.com/free.htm
唢呐：Francesc Fort / TaronjaSatsuma / NENU Folklorical Orchestra，CC BY-SA 4.0：https://commons.wikimedia.org/wiki/File:Suona.ogg
另含 jiemojiemo 的 CC0 实录：https://freesound.org/people/jiemojiemo/sounds/514114/
古筝：Pufermufin，CC0：https://freesound.org/people/Pufermufin/sounds/396868/
钢琴：Alexander Holm / Salamander Grand Piano v3，CC BY 3.0：https://github.com/sfzinstruments/SalamanderGrandPiano
录音切片、重采样及许可说明见 licenses/，原曲与谱面保留各自作者版权。
'''
(O/'修改与检查说明.md').write_text(readme,encoding='utf-8');(P/'README.md').write_text(readme,encoding='utf-8')
with zipfile.ZipFile(O/'Original_Harmony_Stems.zip','w',zipfile.ZIP_STORED) as z:
 for p in (O/'stems').glob('*.flac'):z.write(p,p.name)
with zipfile.ZipFile(O/'Original_Harmony_Project.zip','w',zipfile.ZIP_DEFLATED,compresslevel=2) as z:
 for p in P.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(P))
print('RESTORED',restored,flush=True);print('PERFORMANCE',summary,flush=True);print('PACKAGED',flush=True)
