from pathlib import Path
import numpy as np,soundfile as sf,json,re
from scipy import signal
def bell(x,hz,db,q,sr):
 amp=10**(db/40);w=2*np.pi*hz/sr;al=np.sin(w)/(2*q)
 b=np.array([1+al*amp,-2*np.cos(w),1-al*amp]);a=np.array([1+al/amp,-2*np.cos(w),1-al/amp])
 return signal.lfilter(b/a[0],a/a[0],x,axis=0).astype('float32')
def held(x,d,sr,release=.28):
 goal=round((d+release)*sr)
 if len(x)>=goal:return x[:goal]
 start=min(round(.12*sr),len(x)//4);end=max(start+400,len(x)-round(.06*sr));loop=x[start:end];cross=min(round(.045*sr),len(loop)//4)
 if len(loop)<800:return np.pad(x,((0,max(0,goal-len(x))),(0,0)))
 y=x.copy()
 while len(y)<goal:
  t=np.linspace(0,1,cross,dtype='float32')[:,None];y[-cross:]=y[-cross:]*(1-t)+loop[:cross]*t;y=np.concatenate([y,loop[cross:]])
 return y[:goal]
def catalog(path):
 out=[]
 for p in path.glob('*.wav'):
  m=re.search(r'_([A-G]#?\d)_',p.name)
  if not m:continue
  n=m[1];root=12*(int(n[-1])+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[n[0]]+('#' in n)+12;out.append((root,p))
 return out
def render_reeds(env):
 R,A,SR,N=[env[k] for k in ['R','A','SR','N']];save=env['save'];place=env['place'];shifted=env['shifted'];sd=env['sample_dir'];metrics=env['native_metrics'];rng=np.random.default_rng(517)
 def check(kind,x):
  checks=[]
  for n in A[kind]:
   d=n['off']-n['on'];s=round((n['on']+.025)*SR);e=round(min(n['off'],n['on']+.20)*SR);z=x[s:e]
   row=dict(bar=n['bar'],p=n['p'],duration=d,start_rms=float(np.sqrt(np.mean(z*z))) if len(z) else 0)
   if d>=.9:
    lo=round((n['on']+d*.72)*SR);hi=round((n['on']+d*.92)*SR);row['late_rms']=float(np.sqrt(np.mean(x[lo:hi]**2)))
   checks.append(row)
  metrics[kind]=checks
 for kind,name,target in [('xiao','02_xiao',-28.),('erhu','05_erhu_bed',-35.)]:
  z,_=sf.read(R/(kind+'.wav'),dtype='float32');x=np.zeros((N,2),np.float32);length=min(N,len(z));x[:length]=z[:length]
  if kind=='xiao':
   x=bell(x,2700,-5.,1.05,SR);x=signal.sosfilt(signal.butter(2,3800,fs=SR,output='sos'),x,axis=0).astype('float32')
  for n in A[kind]:
   s=round(n['on']*SR);e=min(N,round(n['off']*SR));d=n['off']-n['on']
   if d>.6:
    t=np.linspace(0,1,e-s);envl=(.88+.17*np.sin(np.pi*t)-.04*t).astype('float32');x[s:e]*=envl[:,None]
  check(kind,x);save(name,x,target,95 if kind=='xiao' else 85)
 suona=[s for s in json.loads((R/'suona_manifest.json').read_text()) if abs(s['pitch']-round(s['pitch']))<.35]
 for kind,name,target,pan in [('suona','01_suona',-24.5,.04),('sax','03_tenor_sax',-25.,-.16),('oboe','04_oboe',-26.5,.17)]:
  buf=np.zeros((N,2),np.float32);library=catalog(sd(kind)) if kind!='suona' else []
  for index,n in enumerate(A[kind]):
   d=n['off']-n['on'];v=n['v']
   if kind=='suona':
    choices=sorted(suona,key=lambda s:abs(s['pitch']-n['p']));dist=abs(choices[0]['pitch']-n['p']);choices=[s for s in choices if abs(s['pitch']-n['p'])<=dist+.6]
    if d>.7:choices=sorted(choices,key=lambda s:s['duration'],reverse=True)[:max(1,len(choices)//2)]
    item=choices[int(rng.integers(len(choices)))];p=sd(kind)/Path(item['path']).name;root=item['pitch']
   else:
    art=('Stac' if d<.19 and n.get('accent') else ('Vib_' if d>.8 else '_NV_')) if kind=='sax' else ('Stacc' if d<.19 and n.get('accent') else ('Vib' if d>1 else 'Sus'))
    choices=[e for e in library if art.lower() in e[1].name.lower()] or library
    root=min({k for k,p in choices},key=lambda k:abs(k-n['p']));choices=[p for k,p in choices if k==root]
    soft=[p for p in choices if ('_v1_' in p.name if kind=='oboe' else '_vl2_' in p.name)];choices=soft or choices;p=choices[int(rng.integers(len(choices)))]
   nxt=A[kind][index+1] if index+1<len(A[kind]) else None
   gap=nxt['on']-n['off'] if nxt else 1.
   # A reed cannot keep three dry pitches ringing at once. The room carries the tail.
   rel=.045 if gap<.08 else min(.28,max(.09,gap*.65))
   x=shifted(p,n['p']-root,max(d+rel+.08,2.),kind);x=held(x,d,SR,rel)
   t=np.minimum(1,np.arange(len(x))/max(1,d*SR));x*=((.9+.13*np.sin(np.pi*t)-.05*t)[:,None]).astype('float32')
   place(buf,x,n['on'],(max(25,v)/85)**1.15,gate=d,release=rel,attack=.012 if d<.3 else .025,pan=pan)
  if kind=='suona':buf=bell(buf,3200,-3.5,.9,SR);buf=signal.sosfilt(signal.butter(2,6500,fs=SR,output='sos'),buf,axis=0).astype('float32')
  if kind=='oboe':buf=bell(buf,2400,-1.5,1.,SR)
  if kind=='sax':buf=signal.sosfilt(signal.butter(2,7500,fs=SR,output='sos'),buf,axis=0).astype('float32')
  check(kind,buf);save(name,buf,target,125 if kind=='suona' else 95)
