from pathlib import Path
import json,numpy as np,soundfile as sf
from scipy import signal,ndimage
R=Path(__file__).resolve().parent;W=R.parent
x,s=sf.read(R/'vocal.wav',dtype='float32');x=x.mean(axis=1)
freq,t,z=signal.stft(x,s,nperseg=4096,noverlap=3072);mag=abs(z)
white=mag/(np.mean(mag,axis=1,keepdims=True)+.00002)**.65
ps=np.arange(48,96);sal=[]
for p in ps:
 f=440*2**((p-69)/12);v=np.zeros(len(t))
 for h in range(1,6):
  b=round(f*h/(s/4096));v+=np.max(white[max(0,b-1):b+2],axis=0)/h**.9
 sal.append(v)
sal=np.array(sal);ch=np.array([sal[ps%12==i].max(axis=0) for i in range(12)])
ch-=ch.mean(axis=0);ch/=np.linalg.norm(ch,axis=0)+1e-8
np.savez(R/'features.npz',ch=ch,t=t,sal=sal,ps=ps)
a=json.loads((W/'fusion/arrangement.json').read_text());mel=json.loads((W/'guofeng/arrangement.json').read_text())['melody']
rows=[]
for n in mel:
 q=n['q'];on=float(np.interp(q,a['grid'],a['seconds']));off=float(np.interp(q+n['d'],a['grid'],a['seconds']))
 if n['bar']<11 or n['bar']>110:continue
 for u in np.arange(on+.07,off,.12):rows.append((u,int(n['p'])%12,n['bar']))
rows=np.array(rows);out=[]
for lo,hi in [(11,34),(47,62),(71,86),(95,110)]:
 rr=rows[(rows[:,2]>=lo)&(rows[:,2]<=hi)];best=[]
 for rate in np.arange(.97,1.031,.005):
  for offset in np.arange(-23,23,.1):
   tt=rr[:,0]*rate+offset;valid=(tt>=0)&(tt<t[-1]);ii=np.clip(np.searchsorted(t,tt),0,len(t)-1)
   score=ch[rr[:,1].astype(int),ii][valid].mean();best.append((float(score),float(rate),float(offset)))
 best.sort(reverse=True);out.append(dict(bars=[lo,hi],best=best[:8]));print(out[-1],flush=True)
(R/'alignment_candidates.json').write_text(json.dumps(out,indent=2))
