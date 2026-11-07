"""Acoustic sample-based arrangement, no oscillators or synth patches.
Run with Python 3.12+: numpy scipy soundfile music21 imageio-ffmpeg.
"""
from pathlib import Path
import json,re,math,functools,subprocess,shutil
import numpy as np
import soundfile as sf
from scipy import signal
import music21 as m
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'outputs' if ROOT.name=='work' else ROOT/'renders'
OUT.mkdir(exist_ok=True,parents=True);(OUT/'stems').mkdir(exist_ok=True)
SR=44100; rng=np.random.default_rng(1701)
score=json.loads((ROOT/'score_events.json').read_text()); events=score['events']
barbeat={b:next(e['beat']-e['t'] for e in events if e['bar']==b) for b in range(1,121)}
# Expressive timing is shared by every part, so accents stay aligned.
grid=np.arange(0,score['beats']+20,.03125)
tempo=np.full(len(grid),112.)
for b in range(1,121):
 mask=(grid>=barbeat[b])&(grid<barbeat[b]+(2 if b==10 else 4))
 if b<=10:tempo[mask]=110
 if b in [9,10,18,26,34,46,54,62,70,78,86,102,110]:tempo[mask]*=np.linspace(1,.96,mask.sum())
 if b>=111:tempo[mask]=np.interp(b,[111,115,118,119,120],[105,101,96,86,69])
tempo[grid>=barbeat[120]+2]=60
seconds=np.r_[0,np.cumsum(60/tempo[:-1]*np.diff(grid))]
def tm(q):return float(np.interp(q,grid,seconds))+.35
DURATION=tm(score['beats'])+9;N=int(DURATION*SR)
def note(p):return int(m.pitch.Pitch(p).midi)
def stage(b):
 return next(label for label,lo,hi in [('A',1,10),('B',11,18),('C',19,26),('D',27,34),('E',35,38),('F',39,46),('G',47,54),('H',55,62),('I',63,70),('J',71,78),('K',79,86),('L',87,94),('M',95,102),('N',103,110),('O',111,120)] if lo<=b<=hi)
levels={'A':45,'B':64,'C':83,'D':83,'E':59,'F':62,'G':86,'H':89,'I':73,'J':94,'K':64,'L':77,'M':102,'N':65,'O':39}
def velocity(e,p):
 v=levels[stage(e['bar'])]
 if stage(e['bar'])=='L':v+=2.8*(e['bar']-87)
 if stage(e['bar'])=='I':v+=max(0,e['bar']-65)*3
 if e['hand']==1:v-=9
 elif p<max(e['p']):v-=12
 else:v+=5
 if e.get('accent'):v+=9
 if e['t']%1==0:v+=2
 if e['bar']>=111:v-=max(0,e['bar']-115)*1.9
 return float(np.clip(v+rng.normal(0,2),24,119))
# Per-pitch ties: combine durations before rendering; never retrigger a tied note.
bykey={}; notes=[]
for e in sorted(events,key=lambda e:(e['beat'],e['hand'])):
 for p in e['p']:
  v=velocity(e,p);key=(e['hand'],p);prev=bykey.get(key)
  if e['tie'] in ['stop','continue'] and prev and abs(prev['q']+prev['d']-e['beat'])<.015:
   prev['d']+=e['d'];prev['tied']=True
  else:
   n=dict(q=e['beat'],d=e['d'],p=p,v=v,bar=e['bar'],hand=e['hand'],accent=e.get('accent',False),tied=False)
   notes.append(n);bykey[key]=n
# Remove duplicate note heads belonging to overlapping notational voices.
uniq={}
for n in notes:
 key=(n['q'],n['p'],n['hand'])
 if key in uniq:
  old=uniq[key];old['d']=max(old['d'],n['d']);old['v']=max(old['v'],n['v'])
 else:uniq[key]=n
notes=sorted(uniq.values(),key=lambda n:n['q'])
samples=ROOT/'samples'
piano={}
for p in (samples/'SalamanderGrandPiano/Samples').glob('*.flac'):
 match=re.fullmatch(r'([A-G]#?\d)v(\d+)\.flac',p.name)
 if match:piano[(note(match[1]),int(match[2]))]=p
def library(sub,offset):
 out=[]
 for p in (samples/'VSCO-2-CE'/sub).rglob('*.wav'):
  match=re.search(r'_([A-G]#?\d)_',p.name)
  if match:out.append((note(match[1])+offset,p))
 return out
bass=library('Strings/Solo Contrabass/Pizz',12)
violins=library('Strings/Violin Section/susVib',12)
cellos=library('Strings/Cello Section/susvib',12)
harps=library('Strings/Harp',0)
used=set()
@functools.lru_cache(maxsize=100)
def read(path):
 used.add(str(Path(path).relative_to(samples)))
 x,sr=sf.read(path,dtype='float32',always_2d=True)
 if x.shape[1]==1:x=np.repeat(x,2,axis=1)
 x=x[:int(sr*14),:2]
 if sr!=SR:x=signal.resample_poly(x,SR,sr).astype('float32')
 # Remove only recording lead-in, preserving the original attack transient.
 z=np.where(np.max(np.abs(x),axis=1)>.00012)[0]
 if len(z):x=x[max(0,min(int(.12*SR),z[0]-int(.002*SR))):]
 return x
def shifted(path,semitones,maxsec):
 x=read(str(path)); ratio=2**(semitones/12)
 count=min(int(len(x)/ratio),int(maxsec*SR))
 if count<=0:return np.zeros((0,2),np.float32)
 positions=np.arange(count)*ratio
 idx=np.minimum(positions.astype(np.int64),len(x)-2);frac=(positions-idx).astype('float32')[:,None]
 return x[idx]*(1-frac)+x[idx+1]*frac
def pianowave(p,v,seconds):
 root=min({k[0] for k in piano},key=lambda k:abs(k-p))
 # Adjacent recorded velocity layers crossfade; never brighten a sine wave.
 lv=np.interp(v,[28,52,79,106],[3,7,11,15]);lo=max(i for i in [3,7,11,15] if i<=lv);hi=min(i for i in [3,7,11,15] if i>=lv)
 a=shifted(piano[root,lo],p-root,seconds)
 if hi!=lo:
  b=shifted(piano[root,hi],p-root,seconds);l=min(len(a),len(b));f=(lv-lo)/(hi-lo);a=a[:l]*(1-f)+b[:l]*f
 return a
def libwave(lib,p,v,seconds):
 root=min({i[0] for i in lib},key=lambda k:abs(k-p));choices=[f for k,f in lib if k==root]
 # Prefer an appropriate sampled dynamic when available, with round robin.
 preferred=[f for f in choices if ('_v1' in f.name if v<78 else '_v2' in f.name or '_v3' in f.name)]
 choices=preferred or choices
 f=choices[int(rng.integers(len(choices)))];return shifted(f,p-root,seconds)
def add(buf,x,on,gain=1,gate=None,release=.2,pan=0,attack=0):
 if not len(x):return
 x=x.copy()
 if gate is not None:
  at=int(gate*SR);end=min(len(x),at+int(release*SR));x=x[:end]
  if at<len(x):x[at:]*=np.linspace(1,0,len(x)-at,dtype=np.float32)[:,None]**1.7
 if attack>0:
  a=min(len(x),int(attack*SR));x[:a]*=np.linspace(0,1,a,dtype=np.float32)[:,None]
 x[:min(120,len(x))]*=np.linspace(0,1,min(120,len(x)),dtype=np.float32)[:,None]
 x[-min(160,len(x)):]*=np.linspace(1,0,min(160,len(x)),dtype=np.float32)[:,None]
 # Natural recorded stereo is retained, with modest seating adjustment.
 x*=np.array([1-max(0,pan)*.55,1+min(0,pan)*.55],np.float32)*gain
 start=max(0,int(on*SR));l=min(len(x),len(buf)-start)
 if l>0:buf[start:start+l]+=x[:l]
def save_stem(name,buf):
 sf.write(OUT/'stems'/(name+'.wav'),buf,SR,subtype='FLOAT')
 print(name,'peak',float(np.max(np.abs(buf))),flush=True)
buf=np.zeros((N,2),np.float32)
for i,n in enumerate(notes):
 q,d,p,v,b=n['q'],n['d'],n['p'],n['v'],n['bar'];st=stage(b)
 on=tm(q)+float(rng.normal(0,.0035))+(0.007 if n['hand']==0 else 0)
 duration=tm(q+d)-tm(q)
 dense=st in ['H','I','L','M']
 gate=duration*(.90 if dense else 1.01)
 if st in ['D','H'] and n['hand']==1 and n['d']<=.5:gate=duration*.58
 # Half-pedal lifted on harmonic changes. Dense runs use shallower pedal.
 boundary=barbeat[b]+(2 if q-barbeat[b]<2 else 4)
 sustain=max(gate,min(tm(boundary)-tm(q),.40 if dense else .88))
 if b>=111:sustain=max(gate,1.5)
 x=pianowave(p,v,sustain+.36)
 add(buf,x,on,gain=.52*(v/85)**.65,gate=sustain,release=.26 if p>54 else .34,pan=np.clip((p-66)/90,-.28,.28))
 if i%500==0:print('piano',i,'/',len(notes),flush=True)
save_stem('01_piano',buf);del buf
# Added arrangement derives harmonic notes from the supplied left-hand part.
def harmony(b):
 ns=[n for n in notes if n['bar']==b and n['hand']==1]
 pcs=sorted({n['p']%12 for n in ns})
 return pcs
def rootnote(b):
 ns=[n['p'] for n in notes if n['bar']==b and n['hand']==1 and abs(n['q']-barbeat[b])<.1]
 return min(ns) if ns else 42
buf=np.zeros((N,2),np.float32)
for b in range(11,111):
 st=stage(b)
 strength={'B':.24,'C':.32,'D':.39,'E':.13,'F':.32,'G':.35,'H':.42,'I':.35,'J':.28,'K':.22,'L':.35,'M':.40,'N':.12}.get(st,0)
 if not strength:continue
 r=rootnote(b)
 while r<31:r+=12
 while r>47:r-=12
 pattern=[(0,1.0,1),(1.5,.45,.54),(2,.8,.84),(3.5,.4,.56)] if st in ['D','F','H','M'] else [(0,1.6,1),(2,1.5,.78)]
 for t,d,g in pattern:
  p=r if t!=3.5 else r+7
  x=libwave(bass,p,79,2.3);add(buf,x,tm(barbeat[b]+t)+.009,strength*g,gate=d*60/112,release=.2,pan=-.04)
save_stem('02_double_bass',buf);del buf
buf=np.zeros((N,2),np.float32)
for b in range(19,121):
 st=stage(b);strength={'C':.12,'D':.08,'E':.045,'G':.15,'H':.11,'I':.14,'J':.19,'K':.065,'L':.16,'M':.22,'N':.15,'O':.07}.get(st,0)
 if not strength:continue
 if st=='L':strength*=.55+(b-87)*.12
 if st=='O':strength*=max(.12,1-(b-111)/9)
 # Use a compact voicing from the actual bass-staff harmony.
 ns=[n for n in notes if n['bar']==b and n['hand']==1 and n['q']-barbeat[b]<.8]
 pitches=sorted({n['p']%12 for n in ns})
 for j,pc in enumerate(pitches[:4]):
  p=pc+60
  if p>79:p-=12
  lib=cellos if j==0 else violins
  if j==0:p-=12
  dur=tm(barbeat[b]+4)-tm(barbeat[b])
  x=libwave(lib,p,74,dur+.7)
  # Bow overlap and a slow phrase swell retain recorded natural vibrato.
  env=1+.12*np.sin(np.linspace(-np.pi/2,3*np.pi/2,len(x)))
  x*=env[:,None].astype('float32')
  add(buf,x,tm(barbeat[b])-.025,strength/(max(1,len(pitches))**.6),gate=dur-.03,release=.65,pan=-.28 if j==0 else .32,attack=.16)
save_stem('03_bowed_strings',buf);del buf
buf=np.zeros((N,2),np.float32)
for b in range(1,121):
 st=stage(b)
 if st not in ['B','E','G','I','J','K','N','O']:continue
 if st in ['B','G','J'] and b%2:continue
 ns=[n for n in notes if n['bar']==b and n['hand']==1 and n['q']-barbeat[b]<1]
 pcs=sorted({n['p']%12 for n in ns})
 gain=.095 if st not in ['N','O'] else .055
 for j,pc in enumerate(pcs[:4]):
  p=pc+60+(12 if j==len(pcs)-1 else 0)
  on=barbeat[b]+(j*.25 if st in ['E','K','O'] else 2+j*.25)
  x=libwave(harps,p,64,3.2);add(buf,x,tm(on),gain,gate=2.6,release=.4,pan=.28)
save_stem('04_harp',buf);del buf
perc=samples/'VSCO-2-CE/VSCO 1 Percussion'
bd=list((perc/'drums/bass').glob('bdrum_muted_mp*.wav'))
sn=list((perc/'drums/snare/drum1').glob('snare1_mp_*.wav'))+list((perc/'drums/snare/drum1').glob('snare1_f_*.wav'))
sh=list((perc/'varWood').rglob('*.wav'))
cy=list((perc/'varMetal/Cymbals/susp').glob('susp_hit_hardmall_mf.wav'))+list((perc/'varMetal/Cymbals/susp').glob('susp_hit_soft*.wav'))
print('Percussion source counts',*[len(x) for x in [bd,sn,sh,cy]],flush=True)
buf=np.zeros((N,2),np.float32)
def hit(files,q,g,gate,pan):
 if not files:return
 path=files[int(rng.integers(len(files)))];x=read(str(path));add(buf,x[:int((gate+.25)*SR)],tm(q)+float(rng.normal(.004,.003)),g,gate=gate,release=.15,pan=pan)
for b in range(11,111):
 st=stage(b)
 gain={'B':.07,'C':.13,'D':.21,'E':.035,'F':.17,'G':.15,'H':.23,'I':.16,'J':.12,'K':.09,'L':.14,'M':.25,'N':.045}.get(st,0)
 if not gain:continue
 q=barbeat[b]
 if st in ['D','F','H','M']:
  for t in [0,1.5,2,2.75]:hit(bd,q+t,gain*(1 if t in [0,2] else .58),.22,0)
  for t in [1,3]:hit(sn,q+t,gain*.60,.16,.08)
 elif st not in ['E','N']:
  for t in [0,2]:hit(bd,q+t,gain*.85,.28,0)
 for k in range(8):hit(sh,q+k*.5,gain*(.36 if k%2 else .23),.18,.24 if k%2 else -.18)
 if b in [19,27,47,55,71,95]:hit(cy,q,.085 if b!=95 else .12,3,.34)
 if b in [26,34,54,62,94,102]:
  for k in range(4):hit(sn,q+3+k*.25,gain*(.16+.05*k),.1,-.1+.08*k)
save_stem('05_acoustic_percussion',buf);del buf
# Natural-room DSP: short early reflections and a dark sparse late tail.
mix=np.zeros((N,2),np.float32)
stem_balance={'01_piano':1.0,'02_double_bass':7.,'03_bowed_strings':14.,'04_harp':8.,'05_acoustic_percussion':4.}
for path in sorted((OUT/'stems').glob('*.wav')):
 x,_=sf.read(path,dtype='float32');mix+=x*stem_balance[path.stem]
wet=np.zeros_like(mix)
for delay,gain in [(.031,.12),(.047,.10),(.071,.075),(.109,.06),(.163,.045),(.233,.034),(.349,.025),(.487,.018),(.673,.013),(.887,.009), (1.129,.006)]:
 d=int(delay*SR);wet[d:,0]+=mix[:-d,1]*gain;wet[d:,1]+=mix[:-d,0]*gain*.97
wet=signal.sosfilt(signal.butter(2,5500,fs=SR,output='sos'),wet,axis=0).astype('float32')
mix+=wet*.42;del wet
mix=signal.sosfilt(signal.butter(2,30,btype='highpass',fs=SR,output='sos'),mix,axis=0).astype('float32')
peak=float(np.max(np.abs(mix)));mix*=.86/max(peak,1e-8)
fade=min(int(5*SR),len(mix));mix[-fade:]*=np.linspace(1,0,fade,dtype=np.float32)[:,None]
sf.write(OUT/'One_Last_Kiss_Acoustic_Remix.wav',mix,SR,subtype='PCM_24')
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(OUT/'One_Last_Kiss_Acoustic_Remix.wav'),'-af','loudnorm=I=-16:TP=-1.5:LRA=11','-ar','48000','-c:a','pcm_s24le',str(OUT/'master.wav')],check=True)
(OUT/'One_Last_Kiss_Acoustic_Remix.wav').unlink();(OUT/'master.wav').rename(OUT/'One_Last_Kiss_Acoustic_Remix.wav')
subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(OUT/'One_Last_Kiss_Acoustic_Remix.wav'),'-c:a','libmp3lame','-b:a','320k',str(OUT/'One_Last_Kiss_Acoustic_Remix.mp3')],check=True)
# Export separately editable piano performance MIDI with the shared timing map.
mid=m.stream.Score();part=m.stream.Part();part.insert(0,m.instrument.Piano());part.insert(0,m.tempo.MetronomeMark(number=112))
for n in notes:
 nn=m.note.Note(n['p']);nn.quarterLength=max(.05,(tm(n['q']+n['d'])-tm(n['q']))*112/60);nn.volume.velocity=int(n['v']);part.insert((tm(n['q'])-.35)*112/60,nn)
mid.insert(0,part);mid.write('midi',fp=OUT/'Piano_Performance.mid')
# Match the half-pedal performance in the editable MIDI.
import struct
mp=OUT/'Piano_Performance.mid';raw=mp.read_bytes();fmt,tracks,division=struct.unpack('>HHH',raw[8:14])
def vlq(n):
 b=[n&127];n>>=7
 while n:b.insert(0,128|(n&127));n>>=7
 return bytes(b)
def mtick(q):return int((tm(q)-.35)*division*112/60)
ped=[]
for b in range(1,121):
 for half in [0,2]:
  if b==10 and half==2:continue
  t=mtick(barbeat[b]+half)
  ped.extend([(max(0,t-10),bytes([0xB0,64,0])),(t+13,bytes([0xB0,64,62 if 55<=b<=102 else 88]))])
ped.append((mtick(score['beats'])+1,bytes([0xB0,64,0])))
ped.sort(key=lambda x:x[0]);tr=b'\x00\xff\x03\x0bPiano pedal';last=0
for t,msg in ped:tr+=vlq(t-last)+msg;last=t
tr+=b'\x00\xff\x2f\x00'
mp.write_bytes(b'MThd'+struct.pack('>IHHH',6,1,tracks+1,division)+raw[14:]+b'MTrk'+struct.pack('>I',len(tr))+tr)
report=dict(duration_seconds=DURATION,piano_note_events=len(notes),source_chord_events=len(events),downloaded_sample_files=len(list(samples.rglob('*.wav')))+len(list(samples.rglob('*.flac'))),used_sample_files=len(used),used_samples=sorted(used),sample_rate=48000,seed=1701,omr_corrected_hand_measures=len(score['corrections']),limitations=['No human listening acceptance yet','Photographic score transcription remains subject to note-for-note review; see corrections and OMR source'])
(OUT/'render_report.json').write_text(json.dumps(report,indent=2))
print('DONE',json.dumps({k:v for k,v in report.items() if k!='used_samples'}),flush=True)
