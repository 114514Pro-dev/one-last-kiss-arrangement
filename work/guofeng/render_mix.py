"""Render guzheng, restrained piano and percussion; mix rendered acoustic VST leads."""
from pathlib import Path
import numpy as np,soundfile as sf,json,re,functools,subprocess,math
from scipy import signal
import imageio_ffmpeg
R=Path(__file__).resolve().parent
O=R.parent.parent/'outputs/Guofeng' if R.name=='guofeng' else R/'renders'
O.mkdir(parents=True,exist_ok=True);(O/'stems').mkdir(exist_ok=True)
SR=44100;rng=np.random.default_rng(20261106)
a=json.loads((R/'arrangement.json').read_text());N=int(a['duration']*SR)
grid=np.array(a['grid']);times=np.array(a['seconds']);barbeat={int(k):v for k,v in a['barbeat'].items()}
def tm(q):return float(np.interp(q,grid,times))+.35
used=set();sources={}
@functools.lru_cache(maxsize=90)
def read(p):
 p=Path(p);used.add(str(p));x,sr=sf.read(p,dtype='float32',always_2d=True)
 if x.shape[1]==1:x=np.repeat(x,2,axis=1)
 if sr!=SR:x=signal.resample_poly(x,SR,sr).astype('float32')
 return x[:int(12*SR),:2]
def pitch_shift(p,semi,length):
 x=read(str(p));rate=2**(semi/12);count=min(int(length*SR),int((len(x)-2)/rate));pos=np.arange(count)*rate;ix=pos.astype('int64');f=(pos-ix).astype('float32')[:,None]
 return x[ix]*(1-f)+x[ix+1]*f
def add(buf,x,on,gain,gate,rel=.25,pan=0):
 x=x.copy();at=int(gate*SR);end=min(len(x),at+int(rel*SR));x=x[:end]
 if at<len(x):x[at:]*=np.linspace(1,0,len(x)-at,dtype='float32')[:,None]**1.8
 for z,flip in [(min(100,len(x)),False),(min(180,len(x)),True)]:
  if z:
   if flip:x[-z:]*=np.linspace(1,0,z,dtype='float32')[:,None]
   else:x[:z]*=np.linspace(0,1,z,dtype='float32')[:,None]
 x*=np.array([1-max(pan,0)*.5,1+min(pan,0)*.5],dtype='float32')*gain
 s=max(0,int(on*SR));l=min(len(x),len(buf)-s)
 if l>0:buf[s:s+l]+=x[:l]
def save(name,x,target):
 # Set relative active loudness; do not normalize every note separately.
 hop=SR//2;ener=np.array([np.sqrt(np.mean(x[i:i+hop]**2)) for i in range(0,len(x),hop)])
 active=ener[ener>max(.00005,float(ener.max())*.06)]
 ref=float(np.percentile(active,60)) if len(active) else 1
 scale=10**(target/20)/max(ref,1e-8);x*=scale
 peak=float(np.max(abs(x)))
 if peak>.72:x*=.72/peak
 sf.write(O/'stems'/(name+'.flac'),x,SR,subtype='PCM_24')
 sources[name]=dict(active_target_db=target,gain=scale,peak=float(np.max(abs(x))),rms=float(np.sqrt(np.mean(x*x))))
 print(name,sources[name],flush=True)
# Leads have their own recorded vibrato and articulation. Preserve breath and bow.
for name,file,target,pan in [('01_dizi_xiao','dizi_xiao.wav',-25.,-.13),('02_erhu','erhu.wav',-24.5,.12)]:
 x,_=sf.read(R/file,dtype='float32');x=x[:N]
 x=signal.sosfilt(signal.butter(2,125 if name.startswith('01') else 105,btype='highpass',fs=SR,output='sos'),x,axis=0).astype('float32')
 # Shape sustained notes without adding artificial vibrato to acoustic recordings.
 notes=a['wind'] if name.startswith('01') else a['erhu']
 env=np.ones(len(x),dtype='float32')
 for n in notes:
  s=int(n['on']*SR);e=min(len(x),int(n['off']*SR))
  if e-s>int(.65*SR):
   t=np.linspace(0,1,e-s);env[s:e]*=(.87+.15*np.sin(np.pi*t)-.07*t).astype('float32')
 x*=env[:,None];x*=np.array([1-max(pan,0)*.5,1+min(pan,0)*.5],np.float32)
 save(name,x,target);del x
guz=json.loads((R/'guzheng_manifest.json').read_text());buf=np.zeros((N,2),np.float32)
for i,n in enumerate(a['guzheng']):
 distance=min(abs(item['pitch']-n['p']) for item in guz);choices=[item for item in guz if abs(item['pitch']-n['p'])==distance]
 # Alternate independent plucks to avoid machine-gun repetition.
 item=choices[int(rng.integers(len(choices)))];p=R/item['path'];semi=n['p']-item['pitch']-item['cents']/100
 gate=max(.32,min(2.1,n['gate']+.19));x=pitch_shift(p,semi,gate+.35)
 gain=(n['v']/90)**1.6*(.62 if n.get('tremolo') else 1)
 add(buf,x,n['on'],gain,gate,rel=.28,pan=np.clip((n['p']-65)/50,-.3,.3))
 if i%700==0:print('guzheng',i,'/',len(a['guzheng']),flush=True)
save('03_guzheng',buf,-27.5);del buf
# Piano uses only the newly orchestrated sparse notes, never the previous full stem.
pdir=R/'samples/piano'
if not pdir.exists():pdir=R.parent/'samples/SalamanderGrandPiano/Samples'
pm={}
for p in pdir.glob('*.flac'):
 mat=re.fullmatch(r'([A-G]#?\d)v(\d+)\.flac',p.name)
 if mat:
  name=mat[1];octave=int(name[-1]);pc={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[name[0]]+('#' in name)
  pm[(12*(octave+1)+pc,int(mat[2]))]=p
buf=np.zeros((N,2),np.float32)
for n in a['piano']:
 root=min({k[0] for k in pm},key=lambda x:abs(x-n['p']));p=pm[root,3]
 x=pitch_shift(p,n['p']-root,n['gate']+.4);add(buf,x,n['on'],(n['v']/65)**1.3,n['gate'],rel=.4,pan=-.04)
save('05_piano_support',buf,-43.5);del buf
pp=R/'samples/percussion';wood=list(pp.glob('wood_click_f_rr*.wav'))+list(pp.glob('wood_click3_vl*.wav'));gong=list(pp.glob('gong_*.wav'))
bd=list((R/'samples/drum').glob('*.wav'))
if not bd:bd=list((R.parent/'samples/VSCO-2-CE/VSCO 1 Percussion/drums/bass').glob('bdrum_muted_mp*.wav'))
buf=np.zeros((N,2),np.float32)
def hit(files,q,g,gate,pan=0):
 if not files:return
 p=files[int(rng.integers(len(files)))];x=read(str(p));x=x/max(.08,float(np.max(abs(x))))*.45
 add(buf,x,tm(q)+rng.normal(.004,.003),g,gate,rel=.25,pan=pan)
for b in range(11,111):
 if b in range(35,39):continue
 q=barbeat[b];strong=27<=b<=34 or 55<=b<=70 or 87<=b<=102
 g=.55 if strong else .28
 if b>=103:g=.12
 for t in [0,2]:hit(bd,q+t,g,.25)
 for t in ([.75,1.5,2.75,3.5] if strong else [1.5,3.5]):hit(wood,q+t,g*(.60 if t in [1.5,3.5] else .35),.16,.25 if t>2 else -.25)
 if strong and b%4==2:
  for t in [3,3.25,3.5,3.75]:hit(wood,q+t,g*.24,.1,-.16+t*.07)
 if b in [19,47,71,95]:hit(gong,q,.12 if b!=95 else .2,4.8,.23)
save('04_drums_wood_gong',buf,-36.5);del buf
mix=np.zeros((N,2),np.float32)
for path in sorted((O/'stems').glob('*.flac')):
 x,_=sf.read(path,dtype='float32');mix+=x
# Early stereo reflections, with a smooth diffused room tail.
wet=np.zeros_like(mix)
for delay,g in [(.027,.12),(.043,.105),(.068,.085),(.097,.065),(.139,.055),(.191,.045),(.263,.035),(.347,.029),(.461,.023),(.607,.017),(.787,.012),(1.019,.008),(1.287,.005)]:
 d=int(delay*SR);wet[d:,0]+=mix[:-d,1]*g;wet[d:,1]+=mix[:-d,0]*g*.93
wet=signal.sosfilt(signal.butter(2,4300,fs=SR,output='sos'),wet,axis=0).astype('float32');mix+=wet*.60
mix=signal.sosfilt(signal.butter(2,38,btype='highpass',fs=SR,output='sos'),mix,axis=0).astype('float32')
mix[-5*SR:]*=np.linspace(1,0,5*SR,dtype='float32')[:,None]
mix*=.85/max(float(np.max(abs(mix))),1e-6)
pre=R/'premaster.wav';sf.write(pre,mix,SR,subtype='FLOAT');del mix,wet
ff=imageio_ffmpeg.get_ffmpeg_exe()
r=subprocess.run([ff,'-hide_banner','-i',str(pre),'-af','loudnorm=I=-16:TP=-1.5:LRA=16:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
stats=json.JSONDecoder().raw_decode(r.stderr[r.stderr.rfind('{'):])[0]
filt='loudnorm=I=-16:TP=-1.5:LRA=16:linear=true:measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}'.format(**stats)
wav=O/'One_Last_Kiss_Guofeng.wav';mp3=wav.with_suffix('.mp3')
subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-i',str(pre),'-af',filt,'-ar','48000','-c:a','pcm_s24le',str(wav)],check=True)
subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-i',str(wav),'-c:a','libmp3lame','-b:a','320k',str(mp3)],check=True)
x,sr=sf.read(wav,dtype='float32');assert np.isfinite(x).all() and np.max(abs(x))<1
check=subprocess.run([ff,'-hide_banner','-i',str(wav),'-af','loudnorm=I=-16:TP=-1.5:LRA=16:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
measured=json.JSONDecoder().raw_decode(check.stderr[check.stderr.rfind('{'):])[0]
report=dict(duration_seconds=len(x)/sr,sample_rate=sr,peak_dbfs=20*math.log10(float(np.max(abs(x)))),clipped_samples=int(np.count_nonzero(abs(x)>=1)),integrated_lufs=float(measured['input_i']),true_peak_dbtp=float(measured['input_tp']),lra=float(measured['input_lra']),stems=sources,guzheng_source_takes=len(guz),used_local_samples=sorted(used),piano_note_count=len(a['piano']),wind_note_count=len(a['wind']),erhu_note_count=len(a['erhu']),guzheng_note_count=len(a['guzheng']),limitations=['No human listening acceptance','Transcription inherits the previous photographic score draft; not certified note-perfect','Instrument registers transposed by whole phrases','Free mini instruments lack full commercial-library legato transitions'])
(O/'render_report.json').write_text(json.dumps(report,indent=2));print('DONE',report['integrated_lufs'],report['true_peak_dbtp'],flush=True)
