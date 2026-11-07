from pathlib import Path
import json,struct,subprocess,shutil
import numpy as np
import soundfile as sf
from scipy import signal
import imageio_ffmpeg
W=Path(__file__).resolve().parent;R=W/'xiao';O=W.parent/'outputs/Xiao'
A=json.loads((R/'arrangement.json').read_text());SR=44100;N=round(A['duration']*SR)
x,sr=sf.read(R/'raw.wav',dtype='float32');assert sr==SR
assert len(x)>N-4
x=np.pad(x,((0,max(0,N-len(x))),(0,0)))[:N]
checks=[]
for n in A['xiao']:
 def rms(t,u):return float(np.sqrt(np.mean(x[round(t*SR):round(u*SR)]**2)))
 item=dict(bar=n['bar'],pitch=n['p'],attack=rms(n['on']+.025,min(n['off'],n['on']+.2)))
 if n['off']-n['on']>.9:item['late']=rms(n['on']+.72*(n['off']-n['on']),n['on']+.92*(n['off']-n['on']))
 checks.append(item)
assert all(n['attack']>.00004 and n.get('late',1)>.00004 for n in checks)
assert all(n['p']%12==n.get('source_pitch',n['p'])%12 for n in A['xiao'])
# Only remove subsonic rumble; retain the instrument's upper harmonics.
x=signal.sosfilt(signal.butter(2,65,btype='highpass',fs=SR,output='sos'),x,axis=0).astype('float32')
levels=np.array([np.sqrt(np.mean(z*z)) for z in np.array_split(x,round(A['duration']*2))]);active=levels[levels>.0001]
gain=min(10**(-23.5/20)/np.percentile(active,60),.78/max(abs(x).max(),1e-8));x*=gain
sf.write(O/'stems/01_xiao_lead.flac',x,SR,subtype='PCM_24');del x
src=(W/'reeds/render_reeds.py').read_text(encoding='utf-8')
tail=src[src.index('# Mix a shared, diffused acoustic room.'):]
tail=tail[:tail.index('report=dict(')]
tail=tail.replace('One_Last_Kiss_Original_Harmony_Reeds.wav','One_Last_Kiss_Xiao.wav')
exec(tail)
report=dict(duration_seconds=len(x)/sr,integrated_lufs=float(st['input_i']),true_peak_dbtp=float(st['input_tp']),clipped_samples=int(np.count_nonzero(abs(x)>=1)),tail_peak_last_second=float(abs(x[-sr:]).max()),xiao_notes=len(checks),silent_attacks=0,silent_long_note_tails=0,removed_parts=['sax','oboe','suona'],pentatonic_rewrite=False,xiao_deharsh_eq=False,manual_listening_verified=False)
assert report['clipped_samples']==0 and report['tail_peak_last_second']<.0001
for k in ['erhu','guzheng','violins','cello','bass','piano','percussion']:
 assert A[k]==json.loads((W/'reeds/arrangement.json').read_text())[k]
report['background_events_unchanged']=True
subprocess.run([ff,'-v','error','-i',str(wav.with_suffix('.mp3')),'-f','null','-'],check=True)
subprocess.run([ff,'-v','error','-y','-ss','53','-i',str(wav),'-t','70','-af','afade=t=in:d=0.2,afade=t=out:st=68:d=2','-b:a','320k',str(O/'Xiao_70s_Preview.mp3')],check=True)
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
for ch,(k,pr) in enumerate([('xiao',73),('erhu',110),('guzheng',107),('violins',48),('cello',42),('bass',43),('piano',0)]):
 ev=[(0,bytes([0xc0+ch,pr]))]
 for n in A[k]:ev.extend([(n['on'],bytes([0x90+ch,int(n['p']),round(np.clip(n['v'],1,127))])),(n['off'],bytes([0x80+ch,int(n['p']),0]))])
 tracks.append(track(k,ev))
ev=[]
for n in A['percussion']:
 p={'lowdrum':35,'wood':76,'gong':52,'frame':38}[n['kind']];v=round(np.clip(n['gain']*100,15,110));ev.extend([(n['on'],bytes([0x99,p,v])),(n['on']+.15,bytes([0x89,p,0]))])
tracks.append(track('Acoustic percussion',ev));(O/'Xiao_FL_Import.mid').write_bytes(b'MThd'+struct.pack('>IHHH',6,1,len(tracks),960)+b''.join(tracks))
(O/'render_report.json').write_text(json.dumps(report,indent=2));shutil.copy2(R/'arrangement.json',O/'arrangement.json')
(O/'修改说明.txt').write_text('移除萨克斯、双簧管、唢呐，改由真实箫采样预置领奏。保留现有铺底及引子，未使用五声调式改写；取消箫降刺 EQ。密集快速段落由古筝承担。箫按乐句适配八度并保留气口、延音及自然尾响。\n时长约4分54秒。已检查长音后段、削波、尾响和 MP3 解码；尚未人工试听验收。\nMIDI 为编辑用音符数据，GM 回放音色与音频成品不同。',encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
