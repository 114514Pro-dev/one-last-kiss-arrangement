from pathlib import Path
import json,copy,subprocess
import numpy as np,soundfile as sf
W=Path(__file__).resolve().parent;R=W/'dizi_repaired';R.mkdir(exist_ok=True)
a=json.loads((W/'fusion/arrangement.json').read_text());mel=json.loads((W/'guofeng/arrangement.json').read_text())['melody'];notes=[]
for n in a['erhu']:
 if 'q' not in n or not any(abs(m['q']-n['q'])<.001 and m['bar']==n['bar'] for m in mel):continue
 m=next(m for m in mel if abs(m['q']-n['q'])<.001 and m['bar']==n['bar'])
 z=copy.deepcopy(n);z['p']=int(m['p'])-(12 if 71<=n['bar']<=78 else 0);z['program']=0
 # Match the former flute register while preserving pitch classes.
 while z['p']>95:z['p']-=12
 while z['p']<71:z['p']+=12
 notes.append(z)
notes.sort(key=lambda n:n['on'])
for n,nxt in zip(notes,notes[1:]):
 if n['phrase']!=nxt['phrase']:n['off']=min(n['off'],nxt['on']-.18)
 elif n['p']==nxt['p']:n['off']=min(n['off'],nxt['on']-.014)
 n['off']=max(n['on']+.06,n['off'])
plan=json.loads((W/'fusion/wind_0.json').read_text());plan['events']=sorted([e for n in notes for e in [[n['on'],144,n['p'],int(np.clip(n['v'],30,116))],[n['off'],128,n['p'],0]]])
(R/'plan.json').write_text(json.dumps(plan));(R/'notes.json').write_text(json.dumps(notes))
subprocess.run([str(W/'guofeng/python32/python.exe'),str(W/'fusion/vst_host.py'),str(W/'guofeng/plugins/Mini_DiZi.dll'),str(R/'plan.json'),str(R/'patch.wav')],stdout=(R/'native.log').open('w'),check=True)
x,sr=sf.read(R/'patch.wav',dtype='float32');checks=[]
for n in notes:
 on=round((n['on']+.025)*sr);off=round(min(n['off'],n['on']+.25)*sr);v=float(np.sqrt(np.mean(x[on:off]**2)));assert v>.00004,(n,v)
 if n['off']-n['on']>.6:
  s=round(n['on']*sr);e=round(n['off']*sr);u=np.linspace(0,1,e-s);x[s:e]*=(.88+.18*np.sin(np.pi*u)-.04*u)[:,None]
 checks.append(v)
gain=json.loads((W.parent/'outputs/Fusion/render_report.json').read_text())['stems']['01_dizi_xiao']['gain']
x*=np.array([1,.97],dtype='float32')*gain
from scipy import signal
x=signal.sosfilt(signal.butter(2,100,btype='highpass',fs=sr,output='sos'),x,axis=0).astype('float32')
y,_=sf.read(W.parent/'outputs/Fusion/stems/01_dizi_xiao.flac',dtype='float32');x=np.pad(x,((0,max(0,len(y)-len(x))),(0,0)))[:len(y)];y+=x
sf.write(R/'01_dizi_xiao.flac',y,sr,subtype='PCM_24')
# Reuse the established mix, MIDI and export workflow with the repaired lead.
src=(W/'restore_dizi_xiao.py').read_text(encoding='utf-8')
src=src.replace("R=W/'dizi_restored'","R=W/'dizi_repaired'").replace("outputs/Dizi_Xiao'","outputs/Dizi_Xiao_Fixed'")
src=src.replace("A['xiao']=old['wind']","A['xiao']=sorted(old['wind']+json.loads((R/'notes.json').read_text()),key=lambda n:n['on'])")
src=src.replace("source=O.parent/'Fusion/stems/01_dizi_xiao.flac'","source=R/'01_dizi_xiao.flac'")
src=src.replace("restored_lead_bit_identical=True","restored_lead_bit_identical=False,repaired_handoff_notes="+str(len(notes)))
src=src.replace('恢复中西合璧 Fusion 版本的原笛箫分轨（逐字节相同）','沿用中西合璧 Fusion 版笛箫音色，补齐原先交给二胡领奏的主题段落')
exec(compile(src,str(W/'restore_dizi_xiao.py'),'exec'))
