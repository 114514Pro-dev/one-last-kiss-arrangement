from pathlib import Path
import json,re,subprocess,shutil,functools
import numpy as np,soundfile as sf
from scipy import signal,ndimage
import imageio_ffmpeg
R=Path(__file__).resolve().parent;W=R.parent;O=W.parent/'outputs/Vocal_Mix_v2';O.mkdir(parents=True,exist_ok=True)
ff=imageio_ffmpeg.get_ffmpeg_exe();SR=44100;hop=441
a=json.loads((W/'xiao/arrangement.json').read_text());intro=a['intro_seconds']
def rms(x):return float(np.sqrt(np.mean(x*x)))
def eq(x,f,g,q=.8):
 A=10**(g/40);w=2*np.pi*f/SR;al=np.sin(w)/(2*q);c=np.cos(w)
 b=np.array([1+al*A,-2*c,1-al*A]);aa=np.array([1+al/A,-2*c,1-al/A]);return signal.lfilter(b/aa[0],aa/aa[0],x,axis=0).astype('float32')
def hp(x,f):return signal.sosfilt(signal.butter(2,f,btype='highpass',fs=SR,output='sos'),x,axis=0).astype('float32')
def lp(x,f):return signal.sosfilt(signal.butter(2,f,fs=SR,output='sos'),x,axis=0).astype('float32')
def env_rms(x):
 return np.sqrt(np.mean(x[:len(x)//hop*hop].reshape(-1,hop,2)**2,axis=(1,2))+1e-12)
def expand(env,n):return np.interp(np.arange(n)/hop,np.arange(len(env)),env).astype('float32')
# Freshly render the first four score bars, so there is no sound carried from the discarded improvisation.
dur=11;clean=np.zeros((dur*SR,2),np.float32)
def pn(s):
 m=re.search(r'([A-G]#?)(-?\d+)',s);return 12*(int(m[2])+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[m[1][0]]+('#' in m[1])
@functools.lru_cache(maxsize=64)
def read(p):
 x,s=sf.read(p,always_2d=True,dtype='float32');x=x[:,:2]
 if x.shape[1]==1:x=np.repeat(x,2,axis=1)
 if s!=SR:x=signal.resample_poly(x,SR,s).astype('float32')
 return x
def place(p,semi,on,gain,gate=None,release=.7,pan=0):
 x=read(str(p));ratio=2**(semi/12);pos=np.arange(min(int((len(x)-2)/ratio),round(7*SR)))*ratio;i=pos.astype(int);f=(pos-i).astype('float32')[:,None];x=(x[i]*(1-f)+x[i+1]*f).copy()
 if gate is not None:
  st=round(gate*SR);end=min(len(x),st+round(release*SR));x=x[:end]
  if st<len(x):x[st:]*=np.cos(np.linspace(0,np.pi/2,len(x)-st))[:,None]**2
 attack=min(len(x),round(.008*SR));x[:attack]*=np.sin(np.linspace(0,np.pi/2,attack))[:,None]**2
 tail=min(len(x),round(.03*SR));x[-tail:]*=np.cos(np.linspace(0,np.pi/2,tail))[:,None]**2
 x*=gain*np.array([1-max(0,pan)*.5,1+min(0,pan)*.5]);st=round(on*SR);n=min(len(x),len(clean)-st)
 if n>0:clean[st:st+n]+=x[:n]
def tm(t):return float(np.interp(t-intro,a['seconds'],a['grid']))*60/112
pianos=list((W/'samples/SalamanderGrandPiano/Samples').glob('*v3.flac'))
for n in a['piano']:
 if not 1<=n['bar']<=4:continue
 p=min(pianos,key=lambda p:abs(pn(p.name)-n['p']));place(p,n['p']-pn(p.name),tm(n['on']),.46*(n['v']/60)**.9,tm(n['off'])-tm(n['on']),.8)
manifest=json.loads((W/'guofeng/guzheng_manifest.json').read_text());rng=np.random.default_rng(197)
for n in a['guzheng']:
 if not 1<=n['bar']<=4:continue
 ds=min(abs(z['pitch']-n['p']) for z in manifest);choices=[z for z in manifest if abs(z['pitch']-n['p'])==ds];z=choices[int(rng.integers(len(choices)))];p=W/'guofeng/samples/guzheng'/Path(z['path']).name
 place(p,n['p']-z['pitch']-z['cents']/100,tm(n['on']),.60*(n['v']/70)**1.3,pan=-.18)
# Match the existing quiet score opening and introduce the ensemble over bars three and four.
b,_=sf.read(R/'bed_aligned.wav',dtype='float32');l,_=sf.read(R/'lead_aligned.wav',dtype='float32');v,_=sf.read(R/'vocal_full.wav',dtype='float32')
ref=rms(b[SR:4*SR]);clean*=np.clip(ref/max(rms(clean[SR:4*SR]),1e-8),.1,3)
n=min(len(clean),len(b));u=np.clip((np.arange(n)/SR-4.2857)/4.2857,0,1);cross=(.5-.5*np.cos(np.pi*u)).astype('float32');b[:n]=clean[:n]*(1-cross[:,None])+b[:n]*cross[:,None]
print('CLEAN OPENING RENDERED',flush=True)
# Vocal EQ, controlled dynamics, de-essing, and a narrow central image.
v=hp(v,90);v=eq(v,260,-2.2,1);v=eq(v,2700,1.2,.8)
e=env_rms(v);db=20*np.log10(e+1e-8);gain=np.minimum(0,-(db+23)*(1-1/2.5));gain=ndimage.gaussian_filter1d(gain,7);v*=expand(10**(gain/20),len(v))[:,None]
e=env_rms(v);voiced=e>.006;ref=float(np.percentile(e[voiced],65));v*=.095/max(ref,1e-8)
# Phrase riding is bounded, so breaths and isolation artifacts are not raised into the foreground.
e=env_rms(v);slow=ndimage.gaussian_filter1d(e,65);ride=np.clip(.075/np.maximum(slow,.025),10**(-3/20),10**(3/20));ride=np.where(slow>.012,ride,1);ride=ndimage.gaussian_filter1d(ride,25);v*=expand(ride,len(v))[:,None]
ess=hp(lp(v,10000),5200);se=env_rms(ess);re=env_rms(v);ratio=se/np.maximum(re,.005);deess=np.clip((ratio-.28)*1.5,0,.55);deess=ndimage.gaussian_filter1d(deess,3);v-=ess*expand(deess,len(v))[:,None]
mid=v.mean(axis=1);side=(v[:,0]-v[:,1])*.5;v=np.column_stack([mid+.35*side,mid-.35*side]).astype('float32')
# A short fade keeps the vocal extraction's file boundary from making a new entrance transient.
v[:round(.025*SR)]*=np.linspace(0,1,round(.025*SR))[:,None]
dv=round(20*SR);db=round(.24*SR);N=max(len(b)+db,len(v)+dv)+3*SR
voice=np.zeros((N,2),np.float32);bed=np.zeros_like(voice);flute=np.zeros_like(voice);voice[dv:dv+len(v)]=v;bed[db:db+len(b)]=b;flute[db:db+len(l)]=l
e=env_rms(voice);act=np.clip((e-.004)/.012,0,1);act=ndimage.maximum_filter1d(act,size=45);act=ndimage.gaussian_filter1d(act,18);activity=expand(act,N)
# Make room in the vocal intelligibility band while preserving the low-frequency foundation.
low=lp(bed,180);body=bed-low;body=eq(body,2200,-2.0,.65)
body*= (1-.20*activity)[:,None];bed=low+body
flute=hp(flute,160);flute*= (1-.80*activity)[:,None];flute[:,0]*=.90
# Set the balance against the actual voiced windows, then hold a stable bus gain.
ve=env_rms(hp(voice,150));be=env_rms(hp(bed+flute,150));mask=(act[:len(ve)]>.8)&(ve>.025)
relative=float(np.median(20*np.log10((ve[mask]+1e-8)/(be[mask]+1e-8))))
backgain=float(np.clip(10**((relative-2.5)/20),.56,1.12));bed*=backgain;flute*=backgain
print('BALANCE',relative,'dB before; backing gain',backgain,flush=True)
# One shared room joins voices and instruments; the vocal send stays small and has pre-delay.
mix=bed+flute+voice;send=(bed+flute)*.085
pred=round(.038*SR);send[pred:]+=voice[:-pred]*.045
t=np.arange(round(1.8*SR))/SR;ir=rng.standard_normal((len(t),2)).astype('float32')*np.exp(-6.9*t[:,None]/1.4);ir[:round(.022*SR)]=0;ir=lp(ir,5200);ir/=np.sqrt(np.sum(ir*ir,axis=0))[None,:];ir*=.48
for c in range(2):mix[:,c]+=signal.fftconvolve(send[:,c],ir[:,c])[:N].astype('float32')
mix=hp(mix,28);mix[:round(.02*SR)]*=np.sin(np.linspace(0,np.pi/2,round(.02*SR)))[:,None]**2
mix[-3*SR:]*=np.cos(np.linspace(0,np.pi/2,3*SR))[:,None]**2
mix*=.87/max(abs(mix).max(),1e-8);sf.write(R/'v2_premaster.wav',mix,SR,subtype='FLOAT')
def measure(p):
 z=subprocess.run([ff,'-hide_banner','-i',str(p),'-af','loudnorm=I=-16:TP=-1.5:LRA=13:print_format=json','-f','null','-'],capture_output=True,text=True,check=True);return json.JSONDecoder().raw_decode(z.stderr[z.stderr.rfind('{'):])[0]
st=measure(R/'v2_premaster.wav');filt='loudnorm=I=-16:TP=-1.5:LRA=13:linear=true:measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}'.format(**st)
wav=O/'One_Last_Kiss_Vocal_Mixed_v2.wav';subprocess.run([ff,'-v','error','-y','-i',str(R/'v2_premaster.wav'),'-af',filt,'-ar','48000','-c:a','pcm_s24le',str(wav)],check=True)
subprocess.run([ff,'-v','error','-y','-i',str(wav),'-b:a','320k',str(wav.with_suffix('.mp3'))],check=True)
subprocess.run([ff,'-v','error','-y','-i',str(wav),'-t','75','-af','afade=t=out:st=73:d=2','-b:a','320k',str(O/'Opening_75s_Preview.mp3')],check=True)
shutil.copy2('inputs/source.lrc',O/'One_Last_Kiss_Vocal_Mixed_v2.lrc')
st=measure(wav);x,sr=sf.read(wav,dtype='float32');assert np.isfinite(x).all() and abs(x).max()<1
report=dict(duration_seconds=len(x)/sr,integrated_lufs=st['input_i'],true_peak_dbtp=st['input_tp'],opening_rebuilt_from_score_bars=[1,2,3,4],preview_starts_at_seconds=0,vocal_delay_seconds=20,backing_offset_seconds=.24,lyrics_unchanged=True,vocal_compression_ratio=2.5,vocal_riding_limit_db=3,backing_bus_gain=backgain,voiced_midband_balance_db=relative-20*np.log10(backgain),manual_listening_verified=False)
(O/'mix_report.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
