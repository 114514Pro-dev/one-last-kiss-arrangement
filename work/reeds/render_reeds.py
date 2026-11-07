from pathlib import Path
import json,re,functools,math,subprocess,sys
import numpy as np,soundfile as sf
from scipy import signal
import imageio_ffmpeg
R=Path(__file__).resolve().parent;W=R.parent
sys.path.insert(0,str(R))
O=W.parent/'outputs/Reeds' if R.name=='reeds' else R/'renders'
O.mkdir(parents=True,exist_ok=True);(O/'stems').mkdir(exist_ok=True)
A=json.loads((R/'arrangement.json').read_text());SR=44100;N=round(A['duration']*SR);rng=np.random.default_rng(690)
def sample_dir(kind):
 p=R/'samples'/kind
 if p.exists():return p
 return {'suona':W/'modal/samples/suona','sax':W/'modal/samples/sax','oboe':W/'modal/samples/oboe','piano':W/'samples/SalamanderGrandPiano/Samples','strings':W/'samples/VSCO-2-CE/Strings','percussion':W/'guofeng/samples/percussion','drum':W/'samples/VSCO-2-CE/VSCO 1 Percussion/drums','guzheng':W/'guofeng/samples/guzheng'}[kind]
select='wind' if '--wind-only' in sys.argv else 'all'
render='--mix-only' not in sys.argv
used={};metrics={};native_metrics={}
if select!='all' or not render:
 previous=json.loads((O/'render_report.json').read_text());used=previous['used_samples'];metrics=previous['stems'];native_metrics=previous['native_note_checks']
@functools.lru_cache(maxsize=110)
def read(p):
 p=Path(p);x,sr=sf.read(p,dtype='float32',always_2d=True)
 if x.shape[1]==1:x=np.repeat(x,2,axis=1)
 if sr!=SR:x=signal.resample_poly(x,SR,sr).astype('float32')
 # Recordable sound only; preserve attack lead-in and natural tail.
 return x[:int(15*SR),:2]
def use(path,kind):
 path=Path(path);used[str(path)]=str(Path(kind)/path.relative_to(sample_dir(kind)))
def shifted(p,semi,dur,kind):
 use(p,kind);x=read(str(p));ratio=2**(semi/12);count=min(round(dur*SR),int((len(x)-2)/ratio));pos=np.arange(count)*ratio;idx=pos.astype('int64');f=(pos-idx).astype('float32')[:,None]
 return x[idx]*(1-f)+x[idx+1]*f
def place(buf,x,on,gain=1,gate=None,release=.5,attack=.003,pan=0,natural=False):
 if len(x)==0:return
 x=x.copy();l=len(x)
 if gate is not None and not natural:
  start=round(gate*SR);end=min(l,start+round(release*SR));x=x[:end];l=len(x)
  if start<l:x[start:]*=np.cos(np.linspace(0,np.pi/2,l-start,dtype='float32'))[:,None]**2
 startfade=min(round(attack*SR),l)
 if startfade:x[:startfade]*=np.sin(np.linspace(0,np.pi/2,startfade,dtype='float32'))[:,None]**2
 endfade=min(l,round((.18 if natural else .025)*SR))
 if endfade:x[-endfade:]*=np.cos(np.linspace(0,np.pi/2,endfade,dtype='float32'))[:,None]**2
 x*=gain*np.array([1-max(0,pan)*.55,1+min(0,pan)*.55],dtype='float32')
 start=max(0,round(on*SR));l=min(l,N-start)
 if l>0:buf[start:start+l]+=x[:l]
def save(name,x,target,highpass=30):
 x=signal.sosfilt(signal.butter(2,highpass,btype='highpass',fs=SR,output='sos'),x,axis=0).astype('float32')
 en=np.array([np.sqrt(np.mean(x[i:i+SR//2]**2)) for i in range(0,N,SR//2)])
 act=en[en>max(.00003,float(en.max())*.045)]
 ref=float(np.percentile(act,60)) if len(act) else 1
 gain=10**(target/20)/max(ref,1e-8);x*=gain
 pk=float(abs(x).max())
 if pk>.78:x*=.78/pk
 metrics[name]=dict(active_target_db=target,rms=float(np.sqrt(np.mean(x*x))),peak=float(abs(x).max()),gain=gain)
 sf.write(O/'stems'/(name+'.flac'),x,SR,subtype='PCM_24');print(name,metrics[name],flush=True)
 (R/'render_checkpoint.json').write_text(json.dumps(dict(stems=metrics,used_samples=used,native_note_checks=native_metrics),indent=2))
from reed_performances import render_reeds
if render:render_reeds(globals())
# Original plucks are allowed to ring. Use longer independent recordings for long notes.
manifest_path=R/'guzheng_manifest.json'
if not manifest_path.exists():manifest_path=W/'guofeng/guzheng_manifest.json'
guz=json.loads(manifest_path.read_text());buf=np.zeros((N,2),np.float32)
for i,n in enumerate(A['guzheng'] if render and select=='all' else []):
 nearest=min(abs(t['pitch']-n['p']) for t in guz)
 choices=[t for t in guz if abs(t['pitch']-n['p'])==nearest]
 if n['off']-n['on']>1:choices=sorted(choices,key=lambda t:t['duration'],reverse=True)[:max(1,len(choices)//2)]
 item=choices[int(rng.integers(len(choices)))];p=sample_dir('guzheng')/Path(item['path']).name
 dur=min(6.,max(2.,n['off']-n['on']+1.3));semi=n['p']-item['pitch']-item['cents']/100
 x=shifted(p,semi,dur,'guzheng');gain=(max(24,n['v'])/90)**1.5
 # Quieter accompaniment, foreground plucked figures in F/I/L and the prelude.
 if n['bar'] and not(39<=n['bar']<=46 or 65<=n['bar']<=70 or 87<=n['bar']<=94):gain*=.74
 place(buf,x,n['on'],gain,pan=np.clip((n['p']-65)/60,-.3,.3),natural=True)
 if i%800==0:print('guzheng',i,flush=True)
if render and select=='all':save('06_guzheng',buf,-30.5,80)
del buf
# Real multi-velocity piano, with harmonic pedal rather than metronomic short gates.
def pname(name):
 match=re.search(r'_([A-G]#?\d)_',name)
 if not match:return None
 p=match[1];return 12*(int(p[-1])+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[p[0]]+('#' in p)
pm={}
for p in sample_dir('piano').glob('*.flac'):
 m=re.match(r'([A-G]#?\d)v(\d+)',p.stem)
 if m:pm[(pname('_'+m[1]+'_'),int(m[2]))]=p
buf=np.zeros((N,2),np.float32)
for n in (A['piano'] if render and select=='all' else []):
 root=min({k[0] for k in pm},key=lambda p:abs(p-n['p']));v=n['v'];layer=3 if v<48 else (7 if v<72 else 11)
 p=pm[root,layer];gate=n['off']-n['on'];x=shifted(p,n['p']-root,gate+1.1,'piano')
 place(buf,x,n['on'],(max(v,25)/80)**.9,gate=gate,release=.85,pan=np.clip((n['p']-58)/100,-.15,.15))
if render and select=='all':save('10_piano_foundation',buf,-31.5,28)
del buf
def lib(sub):
 out=[]
 for p in (sample_dir('strings')/sub).rglob('*.wav'):
  root=pname(p.name)
  if root is not None:out.append((root+12,p))
 return out
libraries={'bass':lib('Solo Contrabass/Pizz'),'cello':lib('Cello Section/susvib'),'violins':lib('Violin Section/susVib')}
for kind,name,target,pan in [('bass','09_double_bass',-27.,-.035),('cello','08_cellos',-27.8,-.23),('violins','07_violin_ensemble',-28.5,.27)]:
 if not render or select!='all':continue
 buf=np.zeros((N,2),np.float32);library=libraries[kind]
 for i,n in enumerate(A[kind]):
  root=min({k for k,p in library},key=lambda k:abs(k-n['p']));choices=[p for k,p in library if k==root]
  pref=[p for p in choices if ('_v1' in p.name if n['v']<74 else '_v2' in p.name or '_v3' in p.name)]
  choices=pref or choices;p=choices[int(rng.integers(len(choices)))];dur=n['off']-n['on'];release=.45 if kind=='bass' else .65
  x=shifted(p,n['p']-root,dur+release+.12,'strings');gain=(max(n['v'],25)/80)**1.25
  if n.get('role')=='harmony':gain*=.65
  if kind!='bass':
   # Bow swells through the note, followed by a real gap only on phrase endings.
   x*=((.90+.12*np.sin(np.linspace(0,np.pi,len(x))))[:,None]).astype('float32')
  place(buf,x,n['on'],gain,gate=dur,release=release,attack=.07 if kind!='bass' else .003,pan=pan)
 save(name,buf,target,32 if kind=='bass' else (55 if kind=='cello' else 125));del buf
# Acoustically recorded drum / wood / gong; no short gate on resonating metal.
per=sample_dir('percussion');drum=sample_dir('drum')
sets={'wood':list(per.glob('wood_click*.wav')),'gong':list(per.glob('gong_*.wav')),'lowdrum':list((drum/'bass').glob('bdrum_muted_mp*.wav')),'frame':list((drum/'snare/drum1').glob('snare1_mp_*.wav'))}
buf=np.zeros((N,2),np.float32)
for n in (A['percussion'] if render and select=='all' else []):
 kind=n['kind'];files=sets[kind]
 if not files:continue
 p=files[int(rng.integers(len(files)))];use(p,'percussion' if kind in ['wood','gong'] else 'drum');x=read(str(p));x=x.copy()* (.4/max(.05,float(abs(x).max())))
 maxlen=7 if kind=='gong' else (1.2 if kind=='lowdrum' else .8)
 x=x[:round(maxlen*SR)]
 place(buf,x,n['on']+rng.normal(.003,.002),n['gain'],natural=True,pan=.18 if kind in ['gong','wood'] else 0)
if render and select=='all':save('11_acoustic_percussion',buf,-33.0,32)
del buf
# Mix a shared, diffused acoustic room. Its tail is allowed to decay to silence.
mix=np.zeros((N,2),np.float32);send=np.zeros_like(mix)
for p in sorted((O/'stems').glob('*.flac')):
 x,_=sf.read(p,dtype='float32');length=min(N,len(x));mix[:length]+=x[:length]
 wet=.17 if 'violin' in p.name or 'cellos' in p.name else (.11 if any(k in p.name for k in ['xiao','suona','sax','oboe']) else .075)
 send[:length]+=x[:length]*wet
irlen=round(2.6*SR);t=np.arange(irlen)/SR
ir=np.random.default_rng(82451).standard_normal((irlen,2)).astype('float32')*np.exp(-6.9*t[:,None]/1.9)
ir[:round(.035*SR)]=0
ir=signal.sosfilt(signal.butter(2,4700,fs=SR,output='sos'),ir,axis=0).astype('float32')
ir/=np.sqrt(np.sum(ir*ir,axis=0))[None,:]
ir*=.58
for delay,g in [(.023,.21),(.039,.18),(.061,.14),(.087,.11),(.123,.075)]:
 ir[round(delay*SR),0]+=g;ir[round((delay+.004)*SR),1]+=g*.93
for c in range(2):mix[:,c]+=signal.fftconvolve(send[:,c],ir[:,c],mode='full')[:N].astype('float32')
del send
mix=signal.sosfilt(signal.butter(2,27,btype='highpass',fs=SR,output='sos'),mix,axis=0).astype('float32')
# Close very gradually only after the score's fermata and the room's decay.
fade=round(3*SR);mix[-fade:]*=np.cos(np.linspace(0,np.pi/2,fade,dtype='float32'))[:,None]**2
mix*=.86/max(float(abs(mix).max()),1e-8)
pre=R/'premaster.wav';sf.write(pre,mix,SR,subtype='FLOAT');del mix
ff=imageio_ffmpeg.get_ffmpeg_exe()
def measure(path):
 r=subprocess.run([ff,'-hide_banner','-i',str(path),'-af','loudnorm=I=-16:TP=-1.5:LRA=15:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
 return json.JSONDecoder().raw_decode(r.stderr[r.stderr.rfind('{'):])[0]
st=measure(pre);filt='loudnorm=I=-16:TP=-1.5:LRA=15:linear=true:measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}'.format(**st)
wav=O/'One_Last_Kiss_Original_Harmony_Reeds.wav'
subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-i',str(pre),'-af',filt,'-ar','48000','-c:a','pcm_s24le',str(wav)],check=True)
subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-i',str(wav),'-c:a','libmp3lame','-b:a','320k',str(wav.with_suffix('.mp3'))],check=True)
st=measure(wav);x,sr=sf.read(wav,dtype='float32');assert np.isfinite(x).all() and abs(x).max()<1
report=dict(duration_seconds=len(x)/sr,intro_seconds=A['intro_seconds'],score_end=A['score_end'],mode=A['mode'],stems=metrics,native_note_checks=native_metrics,integrated_lufs=float(st['input_i']),true_peak_dbtp=float(st['input_tp']),lra=float(st['input_lra']),clipped_samples=int(np.count_nonzero(abs(x)>=1)),used_samples=used,tail_rms_last_second=float(np.sqrt(np.mean(x[-sr:]**2))),tail_peak_last_second=float(abs(x[-sr:]).max()),notes={k:len(A[k]) for k in ['xiao','suona','sax','oboe','erhu','guzheng','bass','cello','violins','piano']})
(O/'render_report.json').write_text(json.dumps(report,indent=2));print('DONE',report['integrated_lufs'],report['true_peak_dbtp'],'seconds',len(x)/sr,flush=True)
