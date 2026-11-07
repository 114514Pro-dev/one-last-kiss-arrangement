from pathlib import Path
import numpy as np,soundfile as sf,json
from scipy import signal
R=Path(__file__).resolve().parent
def yin(x,sr):
 x=signal.resample_poly(x,1,2).astype('float64');sr=sr/2;x-=x.mean();n=len(x)
 ac=signal.fftconvolve(x,x[::-1],mode='full')[n-1:];cs=np.r_[0,np.cumsum(x*x)];tau=np.arange(1,min(int(sr/180),n//2))
 diff=cs[n-tau]+cs[n]-cs[tau]-2*ac[tau];cm=diff*tau/(np.cumsum(diff)+1e-12)
 ids,_=signal.find_peaks(-cm);ids=[i for i in ids if i>sr/1800 and cm[i]<.22]
 if not ids:return None
 k=ids[0]+1;den=cm[k-2]-2*cm[k-1]+cm[k] if 1<k<len(cm) else 0
 d=.5*(cm[k-2]-cm[k])/den if abs(den)>1e-12 else 0
 return 69+12*np.log2(sr/(k+d)/440)
out=[]
for file,license in [('suona_commons.ogg','CC BY-SA 4.0'),('suona_cc0.mp3','CC0')]:
 path=R/'sources'/file
 if not path.exists():continue
 x,sr=sf.read(path,dtype='float32',always_2d=True);mono=x.mean(axis=1);win=int(.12*sr);hop=int(.025*sr);frames=[]
 for pos in range(0,len(x)-win,hop):
  z=mono[pos:pos+win]
  p=yin(z,sr) if np.sqrt(np.mean(z*z))>.012 else None
  frames.append((pos/sr,p))
 groups=[];group=[]
 for t,p in frames:
  if p is not None and 66<p<98 and (not group or abs(p-np.median([a[1] for a in group]))<.5):group.append((t,p))
  else:
   if len(group)>=8:groups.append(group)
   group=[]
 if len(group)>=8:groups.append(group)
 print(file,'segments',[(round(g[0][0],2),round(g[-1][0]+.12-g[0][0],2),round(float(np.median([z[1] for z in g])),2)) for g in groups],flush=True)
 for i,g in enumerate(groups):
  p=float(np.median([z[1] for z in g]));start=max(0,int((g[0][0]-.015)*sr));end=min(len(x),int((g[-1][0]+.10)*sr));z=x[start:end].copy()
  if z.shape[1]==1:z=np.repeat(z,2,axis=1)
  z*=.5/max(.01,float(np.max(abs(z))));f=min(len(z)//3,int(.035*sr));z[:f]*=np.linspace(0,1,f)[:,None];z[-f:]*=np.linspace(1,0,f)[:,None]
  dst=R/'samples/suona'/f'{path.stem}_{i:02d}_{round(p)}.wav';dst.parent.mkdir(parents=True,exist_ok=True);sf.write(dst,z,sr,subtype='PCM_24');out.append(dict(path=str(dst.relative_to(R)),pitch=p,source=file,start=start/sr,duration=len(z)/sr,license=license))
(R/'suona_manifest.json').write_text(json.dumps(out,indent=2));print('SAMPLES',len(out),flush=True)
