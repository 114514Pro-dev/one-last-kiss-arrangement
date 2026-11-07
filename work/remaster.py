from pathlib import Path
import numpy as np,soundfile as sf
from scipy import signal
import subprocess,imageio_ffmpeg,json
root=Path(__file__).resolve().parent.parent/'outputs'
SR=44100
mix=None
balance={'01_piano':1.,'02_double_bass':7.,'03_bowed_strings':14.,'04_harp':8.,'05_acoustic_percussion':4.}
for p in sorted((root/'stems').glob('*.wav')):
 x,sr=sf.read(p,dtype='float32');x*=balance[p.stem]
 if mix is None:mix=x
 else:mix+=x
wet=np.zeros_like(mix)
for delay,gain in [(.031,.12),(.047,.10),(.071,.075),(.109,.06),(.163,.045),(.233,.034),(.349,.025),(.487,.018),(.673,.013),(.887,.009),(1.129,.006)]:
 d=int(delay*SR);wet[d:,0]+=mix[:-d,1]*gain;wet[d:,1]+=mix[:-d,0]*gain*.97
wet=signal.sosfilt(signal.butter(2,5500,fs=SR,output='sos'),wet,axis=0).astype('float32')
mix+=wet*.42;del wet
mix=signal.sosfilt(signal.butter(2,30,btype='highpass',fs=SR,output='sos'),mix,axis=0).astype('float32')
peak=float(np.max(abs(mix)));mix*=.86/peak
mix[-5*SR:]*=np.linspace(1,0,5*SR,dtype='float32')[:,None]
sf.write(root/'premaster.wav',mix,SR,subtype='FLOAT');del mix
ff=imageio_ffmpeg.get_ffmpeg_exe()
cmd=[ff,'-hide_banner','-y','-i',str(root/'premaster.wav'),'-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-ar','48000','-c:a','pcm_s24le',str(root/'One_Last_Kiss_Acoustic_Remix.wav')]
r=subprocess.run(cmd,capture_output=True,text=True,check=True);(root/'mastering_log.txt').write_text(r.stderr)
subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-i',str(root/'One_Last_Kiss_Acoustic_Remix.wav'),'-c:a','libmp3lame','-b:a','320k',str(root/'One_Last_Kiss_Acoustic_Remix.mp3')],check=True)
(root/'premaster.wav').unlink()
# Lossless editable stems, balanced and sharing a common amount of headroom.
for p in sorted((root/'stems').glob('*.wav')):
 x,sr=sf.read(p,dtype='float32');x*=balance[p.stem]*.65
 sf.write(p.with_suffix('.flac'),x,sr,subtype='PCM_24')
print('MASTER COMPLETE',flush=True)
