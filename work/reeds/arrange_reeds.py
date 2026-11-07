"""Original score melody and harmony with suona, xiao, saxophone and oboe."""
from pathlib import Path
import json,copy,math
import numpy as np
R=Path(__file__).resolve().parent;W=R.parent
base=R/'foundation.json'
if not base.exists():base=W/'fusion/arrangement.json'
A=json.loads(base.read_text());rng=np.random.default_rng(1723)
grid=np.array(A['grid']);seconds=np.array(A['seconds']);bb={int(k):v for k,v in A['barbeat'].items()}
def tm(q):return A['intro_seconds']+float(np.interp(q,grid,seconds))
def stage(b):return next(l for l,a,z in [('A',1,10),('B',11,18),('C',19,26),('D',27,34),('E',35,38),('F',39,46),('G',47,54),('H',55,62),('I',63,70),('J',71,78),('K',79,86),('L',87,94),('M',95,102),('N',103,110),('O',111,120)] if a<=b<=z)
# Restore the unquantized pitch/harmony foundation; keep the reed-oriented balance.
out={k:copy.deepcopy(A[k]) for k in ['guzheng','piano','bass','cello','violins','percussion']}
out.update(suona=[],xiao=[],sax=[],oboe=[],erhu=[])
for n in out['violins']:
 if n.get('role')=='melody':n['v']-=13
mel=R/'source_melody.json'
if not mel.exists():mel=W/'guofeng/arrangement.json'
source=json.loads(mel.read_text())['melody']
# No pentatonic pitch substitution: use the source melody directly.
mapped=[dict(n,render_pitch=n['p']) for n in source]
def add(kind,on,p,d,v,b,**kw):
 n=dict(on=float(on),off=float(on+d),p=int(p),v=float(v),bar=b,**kw);out[kind].append(n);return n
levels={'A':54,'B':76,'C':86,'D':90,'E':59,'F':73,'G':79,'H':90,'I':80,'J':94,'K':64,'L':84,'M':95,'N':68,'O':49}
for n in mapped:
 b=n['bar'];st=stage(b);p=n['render_pitch'];q=n['q'];dur=tm(q+n['d'])-tm(q)
 if st=='K' or st=='O' and b>=118:continue
 owner={'A':'oboe','O':'oboe','B':'sax','C':'suona','D':'suona','E':'oboe','F':'sax','G':'oboe','H':'suona','I':'oboe','J':'suona','L':'sax','M':'suona','N':'sax'}[st]
 if st=='C' and b>=23:owner='sax'
 if st=='G' and b>=51:owner='suona'
 if st=='H' and b>=59:owner='sax'
 if st=='I' and b>=65:continue
 if st=='L':
  # Let the existing guzheng semiquavers carry movement; reeds sing over them.
  if abs(q-round(q))>.02:continue
  dur=max(dur,.46)
 if st=='J':p-=12
 if owner=='sax':
  if st not in ['F']:p-=24 if st=='L' and b>=91 else 12
  while p<48:p+=12
  while p>77:p-=12
 elif owner=='oboe':
  p-=12
  while p<58:p+=12
  while p>85:p-=12
 else:
  while p<71:p+=12
  while p>88:p-=12
 on=tm(q)+(0.013 if owner=='sax' else .006)+rng.normal(0,.002)
 add(owner,on,p,dur,levels[st]+(5 if n.get('accent') else 0),b,q=q,phrase=(b-1)//2,accent=n.get('accent',False),source_pitch=n['p'])
# Soft xiao answers use original D#/F# motifs, not a five-note scale restriction.
ig=np.array(A['intro_grid']);its=np.array(A['intro_times'])
def im(q):return .35+float(np.interp(q,ig,its))
for q,p,d in [(2,51,1),(3.25,54,.6),(6,51,.6),(7,54,.7),(10,51,.6),(11,54,.6),(14,51,1.2),(18,59,.7),(19,63,.7),(22,54,.6),(23,51,.7),(26,54,.7),(27,51,.7),(29,54,.6),(30,51,.7)]:
 add('xiao',im(q),p,im(q+d)-im(q),51+(q>16)*5,0,phrase=int(q//8),program=6)
for n in source:
 if 79<=n['bar']<=86:
  add('xiao',tm(n['q']),n['p']-12,tm(n['q']+n['d'])-tm(n['q']),64,n['bar'],phrase=(n['bar']-1)//2,program=6,source_pitch=n['p'])
for b in range(1,121):
 st=stage(b)
 if st=='O':
  root=[n for n in out['piano'] if n['bar']==b and n['p']<48]
  pc=root[0]['p']%12 if root else 6
  p={1:63,3:58,4:59,6:54,8:56,11:63}.get(pc,54)
  add('xiao',tm(bb[b])+.05,p,tm(bb[b]+4)-tm(bb[b])-.15,47,b,phrase=(b-1)//2,program=6)
 elif b%2==0 and st in ['C','D','G','H','J','M']:
  for t,p,d in [(2.75,59,.45),(3.35,61,.5)]:add('xiao',tm(bb[b]+t),p,tm(bb[b]+t+d)-tm(bb[b]+t),48,b,phrase=b,program=6)
 # Erhu is a single soft bowed support line, never a lead or impossible chord stack.
 roots=[n for n in out['bass']+out['piano'] if n['bar']==b and n['p']<48]
 if roots:
  pc=roots[0]['p']%12;pad={1:64,3:66,4:68,6:70,8:71,11:75}.get(pc,66)
  add('erhu',tm(bb[b])+.08,pad,tm(bb[b]+(2 if b==10 else 4))-tm(bb[b])+.12,43 if st not in ['J','M'] else 48,b,phrase=(b-1)//2,program=3)
# Responses quote the original D#/C# movement.
for b in [18,26,34,46,54,62,70,78,86,94,102,110]:
 q=bb[b]+2.5
 for t,p,d in [(0,75,.4),(.55,73,.55)]:
  if not any(n['bar']==b and n['on']>tm(bb[b]+2) for n in out['oboe']):add('oboe',tm(q+t)+.012,p,tm(q+t+d)-tm(q+t),60,b,phrase=b)
for q,p,d in [(26,75,.6),(27,78,.6),(28.2,75,.7),(29.2,78,.7),(30.2,75,1.1)]:add('oboe',im(q),p,im(q+d)-im(q),56,0,phrase=7)
# Restore the source ending motif and tied F# final, rather than the added yu cadence.
for n in source:
 if n['bar']>=118:
  add('suona',tm(n['q']),n['p']-12,tm(n['q']+n['d'])-tm(n['q']),54,n['bar'],phrase=60,accent=False,source_pitch=n['p'])
for kind in ['xiao','suona','sax','oboe','erhu']:
 ns=sorted(out[kind],key=lambda n:n['on'])
 for i,n in enumerate(ns):
  nxt=ns[i+1] if i+1<len(ns) else None
  if nxt:
   if n['phrase']!=nxt['phrase'] and kind!='erhu':n['off']=min(n['off'],nxt['on']-.17)
   elif n['off']>nxt['on']-.04:n['off']=min(n['off']+.018,nxt['on']+.012)
   if n['p']==nxt['p']:n['off']=min(n['off'],nxt['on']-.014)
  n['off']=max(n['on']+.07,n['off'])
 out[kind]=ns
out.update({k:copy.deepcopy(A[k]) for k in ['duration','intro_seconds','score_end','barbeat','grid','seconds','intro_grid','intro_times']})
out['mode']=dict(name='Original score pitch and harmony; no pentatonic quantization',pitch_classes=sorted({n['p']%12 for n in source}),notes=['B','C#','D#','E','F#','G#','A#'],basis='Restore source melody, bass and ending; retain current reed instrumentation and soft xiao')
for kind in ['guzheng','piano','bass','cello','violins']:
 assert [(n['p'],n['on'],n['off']) for n in out[kind]]==[(n['p'],n['on'],n['off']) for n in A[kind]]
for kind in ['suona','sax','oboe']:
 assert all(n['p']%12==n['source_pitch']%12 for n in out[kind] if 'source_pitch' in n)
(R/'arrangement.json').write_text(json.dumps(out,indent=2))
for kind,prog,params in [('xiao',6,{'1':.06,'2':.3,'14':.80,'12':.38,'3':0,'7':.8}),('erhu',3,{'0':.07,'1':.4,'13':.85,'11':.45,'7':0,'5':.8})]:
 ev=[]
 for n in out[kind]:ev.extend([[n['on'],144,n['p'],round(n['v'])],[n['off'],128,n['p'],0]])
 (R/(kind+'_plan.json')).write_text(json.dumps(dict(duration=A['duration'],program=prog,events=sorted(ev),parameters=params),indent=2))
print('MODE',out['mode']['notes'],'NOTES',{k:len(v) for k,v in out.items() if k in ['xiao','suona','sax','oboe','erhu','guzheng','piano','bass','cello','violins']},flush=True)
