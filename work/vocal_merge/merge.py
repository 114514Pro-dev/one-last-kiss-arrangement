from pathlib import Path
import json,subprocess,shutil,re
import numpy as np,soundfile as sf
from scipy import signal,ndimage
import imageio_ffmpeg
R=Path(__file__).resolve().parent;W=R.parent;O=W.parent/'outputs/Vocal_Mix';O.mkdir(parents=True,exist_ok=True)
ff=imageio_ffmpeg.get_ffmpeg_exe();a=json.loads((W/'fusion/arrangement.json').read_text());intro=a['intro_seconds'];SR=44100
g=np.array(a['grid']);s=np.array(a['seconds']);scorebeats=478;scoreend=float(np.interp(scorebeats,g,s))
# Inverse tempo map: the piano rubato returns to the reference's 112 BPM grid.
commands=[];last=None
for q in np.arange(0,scorebeats,.25):
 t=float(np.interp(q,g,s));dt=float(np.interp(q+.25,g,s)-np.interp(q,g,s));ratio=dt/(.25*60/112)
 if last is None or abs(ratio-last)>.0003:commands.append(f'{t:.6f} rubberband tempo {ratio:.8f};');last=ratio
commands.append(f'{scoreend:.6f} rubberband tempo 1.0;');(R/'tempo_commands.txt').write_text('\n'.join(commands))
N=round(a['duration']*SR);cut=round(intro*SR)
base=np.zeros((N,2),np.float32);lead=None
for p in (W.parent/'outputs/Dizi_Xiao_Fixed/stems').glob('*.flac'):
 x,sr=sf.read(p,dtype='float32');assert sr==SR
 if 'dizi' in p.name:lead=x
 else:base[:len(x)]+=x
assert lead is not None
for name,x in [('bed',base),('lead',lead)]:
 sf.write(R/f'{name}_body.wav',x[cut:],SR,subtype='FLOAT')
 subprocess.run([ff,'-v','error','-y','-i',str(R/f'{name}_body.wav'),'-af','asendcmd=f=tempo_commands.txt,rubberband=tempo=1.01818182:transients=mixed:channels=together','-c:a','pcm_f32le',str(R/f'{name}_aligned.wav')],cwd=R,check=True)
print('RETIME DONE',flush=True)
# Restore the missing 20-second vocal-file offset; the supplied LRC stays unchanged.
vsource=Path('inputs/vocal.mp4')
subprocess.run([ff,'-v','error','-y','-i',str(vsource),'-ar',str(SR),'-c:a','pcm_f32le',str(R/'vocal_full.wav')],check=True)
v,_=sf.read(R/'vocal_full.wav',dtype='float32');b,_=sf.read(R/'bed_aligned.wav',dtype='float32');l,_=sf.read(R/'lead_aligned.wav',dtype='float32')
delayv=round(20*SR);delayb=round(.24*SR);length=max(len(b)+delayb,len(v)+delayv)+round(3*SR)
voice=np.zeros((length,2),np.float32);bed=np.zeros_like(voice);flute=np.zeros_like(voice)
voice[delayv:delayv+len(v)]=v;bed[delayb:delayb+len(b)]=b;flute[delayb:delayb+len(l)]=l
# Slow activity envelope makes room for singing without pumping between syllables.
hop=441;mono=np.sqrt(np.mean(voice[:length//hop*hop].reshape(-1,hop,2)**2,axis=(1,2)))
act=np.clip((mono-.003)/.012,0,1);act=ndimage.maximum_filter1d(act,size=39);act=ndimage.gaussian_filter1d(act,14)
env=np.interp(np.arange(length)/hop,np.arange(len(act)),act).astype('float32')
flute*= (1-.68*env)[:,None]
mix=bed+flute
# Shared acoustic room; only accompaniment is retimed, never the singer.
irlen=round(2.6*SR);t=np.arange(irlen)/SR;ir=np.random.default_rng(82451).standard_normal((irlen,2)).astype('float32')*np.exp(-6.9*t[:,None]/1.9);ir[:round(.035*SR)]=0
ir=signal.sosfilt(signal.butter(2,4700,fs=SR,output='sos'),ir,axis=0).astype('float32');ir/=np.sqrt(np.sum(ir*ir,axis=0))[None,:];ir*=.58
for d,k in [(.023,.21),(.039,.18),(.061,.14),(.087,.11),(.123,.075)]:ir[round(d*SR),0]+=k;ir[round((d+.004)*SR),1]+=k*.93
for c in range(2):mix[:,c]+=signal.fftconvolve(mix[:,c]*.10,ir[:,c])[:length].astype('float32')
mix=signal.sosfilt(signal.butter(2,27,btype='highpass',fs=SR,output='sos'),mix,axis=0).astype('float32')
# Keep bass foundation stable; bring the supplied vocal into the foreground.
active=mono[mono>.008];vref=float(np.percentile(active,65));vgain=min(.115/max(vref,1e-7),4.)
voice*=vgain
mix+=voice
mix[-3*SR:]*=np.cos(np.linspace(0,np.pi/2,3*SR))[:,None]**2
mix*=.85/max(abs(mix).max(),1e-8);sf.write(R/'premaster.wav',mix,SR,subtype='FLOAT')
def measure(p):
 z=subprocess.run([ff,'-hide_banner','-i',str(p),'-af','loudnorm=I=-16:TP=-1.5:LRA=14:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
 return json.JSONDecoder().raw_decode(z.stderr[z.stderr.rfind('{'):])[0]
st=measure(R/'premaster.wav');filt='loudnorm=I=-16:TP=-1.5:LRA=14:linear=true:measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}'.format(**st)
wav=O/'One_Last_Kiss_Vocal_Dizi_Xiao.wav'
subprocess.run([ff,'-v','error','-y','-i',str(R/'premaster.wav'),'-af',filt,'-ar','48000','-c:a','pcm_s24le',str(wav)],check=True)
subprocess.run([ff,'-v','error','-y','-i',str(wav),'-b:a','320k',str(wav.with_suffix('.mp3'))],check=True)
subprocess.run([ff,'-v','error','-y','-ss','18','-i',str(wav),'-t','70','-af','afade=t=in:d=0.15,afade=t=out:st=68:d=2','-b:a','320k',str(O/'Vocal_70s_Preview.mp3')],check=True)
shutil.copy2('inputs/source.lrc',O/'One_Last_Kiss_Vocal_Dizi_Xiao.lrc')
st=measure(wav);x,sr=sf.read(wav,dtype='float32');assert np.isfinite(x).all() and abs(x).max()<1
report=dict(removed_improvisation_seconds=intro,vocal_delay_seconds=20,backing_grid_bpm=112,backing_offset_seconds=.24,pitch_shift_semitones=0,vocal_time_stretched=False,lyrics_timestamps_unchanged=True,duration_seconds=len(x)/sr,integrated_lufs=st['input_i'],true_peak_dbtp=st['input_tp'],manual_listening_verified=False)
(O/'alignment_report.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
