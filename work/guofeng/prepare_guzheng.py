import numpy as np,soundfile as sf,json
from scipy import signal
from pathlib import Path
R=Path(__file__).resolve().parent
x,sr=sf.read(R/'guzheng_excerpt.wav',dtype='float32');mono=x.mean(axis=1);hop=220
en=np.array([np.sqrt(np.mean(mono[i:i+hop]**2)) for i in range(0,len(mono),hop)])
flux=np.maximum(0,en-np.r_[np.zeros(3),en[:-3]])
peaks,_=signal.find_peaks(flux,height=max(.004,np.percentile(flux,96)),distance=int(.5*sr/hop),prominence=.003)
print('onsets',len(peaks),flush=True)
def pitch_yin(a):
 a=signal.resample_poly(a,1,2);fs=sr/2
 a=a[:8192].astype('float64');a-=a.mean();n=len(a)
 ac=signal.fftconvolve(a,a[::-1],mode='full')[n-1:]
 cs=np.r_[0,np.cumsum(a*a)];maxlag=min(int(fs/50),n//2)
 tau=np.arange(1,maxlag);diff=(cs[n-tau]-cs[0])+(cs[n]-cs[tau])-2*ac[tau]
 cm=diff*tau/(np.cumsum(diff)+1e-12);lo=int(fs/2200)
 cand,_=signal.find_peaks(-cm)
 cand=[i for i in cand if i>=lo and cm[i]<.18]
 if not cand:return None
 k=cand[0]+1
 y=diff/(cs[n]+1e-12)
 den=(cm[k-2]-2*cm[k-1]+cm[k]) if 1<k<len(cm) else 0
 shift=.5*(cm[k-2]-cm[k])/den if abs(den)>1e-10 else 0
 hz=fs/(k+shift);return 69+12*np.log2(hz/440)
out=[];(R/'samples/guzheng').mkdir(parents=True,exist_ok=True)
for ii,k in enumerate(peaks):
 start=max(0,int(k*hop)-int(.012*sr));end=min(len(x),int(peaks[ii+1]*hop)-int(.025*sr) if ii+1<len(peaks) else start+int(5*sr))
 if (end-start)/sr<.65:continue
 a=pitch_yin(mono[start+int(.08*sr):min(end,start+int(.48*sr))]);b=pitch_yin(mono[start+int(.28*sr):min(end,start+int(.70*sr))])
 if a is None or b is None or abs(a-b)>.45 or abs(a-round(a))>.35:continue
 p=int(round(a))
 if not 35<=p<=96:continue
 z=x[start:end].copy();z=z[:int(6*sr)];z[:120]*=np.linspace(0,1,120)[:,None];z[-500:]*=np.linspace(1,0,500)[:,None]
 peak=float(np.max(abs(z)))
 if peak<.025:continue
 z*=.55/peak
 dest=R/'samples/guzheng'/f'guzheng_m{p:03d}_take{ii:03d}.wav';sf.write(dest,z,sr,subtype='PCM_24')
 out.append(dict(path=str(dest.relative_to(R)),pitch=p,cents=float((a-p)*100),source_seconds=start/sr,duration=len(z)/sr))
(R/'guzheng_manifest.json').write_text(json.dumps(out,indent=2));print('Usable',len(out),'pitches',sorted({e['pitch'] for e in out}),flush=True)
