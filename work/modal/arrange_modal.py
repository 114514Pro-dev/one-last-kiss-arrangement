"""C# yu (E gong pentatonic) re-arrangement of the existing acoustic foundation."""
from pathlib import Path
import json,copy,math
import numpy as np
R=Path(__file__).resolve().parent;W=R.parent
base=R/'foundation.json'
if not base.exists():base=W/'fusion/arrangement.json'
A=json.loads(base.read_text());rng=np.random.default_rng(1723)
PCS={1,4,6,8,11};grid=np.array(A['grid']);seconds=np.array(A['seconds']);bb={int(k):v for k,v in A['barbeat'].items()}
def tm(q):return A['intro_seconds']+float(np.interp(q,grid,seconds))
def stage(b):return next(l for l,a,z in [('A',1,10),('B',11,18),('C',19,26),('D',27,34),('E',35,38),('F',39,46),('G',47,54),('H',55,62),('I',63,70),('J',71,78),('K',79,86),('L',87,94),('M',95,102),('N',103,110),('O',111,120)] if a<=b<=z)
def nearest(p):return min([q for q in range(p-3,p+4) if q%12 in PCS],key=lambda q:(abs(q-p),-q))
def root_map(p,b):
 pc=p%12
 if pc==3:
  pc=6 if b in [20,24,48,52,72,76] else 8
  return min([q for q in range(p-8,p+9) if q%12==pc],key=lambda q:abs(q-p))
 return nearest(p)
# Rewrite every pitched foundation voice, retaining timing and bass weight.
out={k:copy.deepcopy(A[k]) for k in ['guzheng','piano','bass','cello','violins','percussion']}
out.update(suona=[],xiao=[],sax=[],oboe=[],erhu=[])
for kind in ['guzheng','piano','bass','cello','violins']:
 for n in out[kind]:
  old=n['p'];b=n['bar'];n['source_pitch']=old
  isroot=kind=='bass' or kind=='cello' and n.get('role')=='root' or kind=='piano' and old<=47
  n['p']=root_map(old,b) if isroot else nearest(old)
  if kind=='violins' and n.get('role')=='melody':n['v']-=13
  if kind=='piano' and b==0 and old%12==3 and old<48:n['p']=root_map(old,1)
  if b==120:
   # A C# yu cadence; no lingering F#-major third or non-modal leading tone.
   if isroot:n['p']=min([q for q in range(old-7,old+8) if q%12==1],key=lambda q:abs(q-old))
   elif kind in ['cello','violins','piano']:n['p']=nearest(old)
 # Pentatonic mapping can collapse adjacent chord voices into the same unison.
 keep={}
 for n in out[kind]:
  key=(round(n['on']*35),n['p']);old=keep.get(key)
  if old:
   old['off']=max(old['off'],n['off']);old['v']=max(old['v'],n['v'])
  else:keep[key]=n
 out[kind]=sorted(keep.values(),key=lambda n:n['on'])
mel=R/'source_melody.json'
if not mel.exists():mel=W/'guofeng/arrangement.json'
source=json.loads(mel.read_text())['melody']
# Dynamic programming preserves the direction/shape of the original hook.
mapped=[]
for block in range(30):
 ns=[n for n in source if block*4+1<=n['bar']<=block*4+4]
 if not ns:continue
 cand=[[p for p in range(n['p']-2,n['p']+3) if p%12 in PCS] for n in ns]
 cost=[{p:abs(p-ns[0]['p'])**2 for p in cand[0]}];back=[]
 for i in range(1,len(ns)):
  orig=ns[i]['p']-ns[i-1]['p'];row={};br={}
  for p in cand[i]:
   choices=[]
   for prev,oldcost in cost[-1].items():
    diff=p-prev;pen=.45*(diff-orig)**2
    if orig and diff*orig<0:pen+=6
    if orig==0 and diff!=0:pen+=8
    if abs(orig)>=2 and diff==0:pen+=2
    choices.append((oldcost+abs(p-ns[i]['p'])**2+pen,prev))
   row[p],br[p]=min(choices)
  cost.append(row);back.append(br)
 pitch=min(cost[-1],key=cost[-1].get);ps=[pitch]
 for br in reversed(back):pitch=br[pitch];ps.append(pitch)
 for n,p in zip(ns,reversed(ps)):mapped.append(dict(n,modal_pitch=p))
def add(kind,on,p,d,v,b,**kw):
 n=dict(on=float(on),off=float(on+d),p=int(p),v=float(v),bar=b,**kw);out[kind].append(n);return n
levels={'A':54,'B':76,'C':86,'D':90,'E':59,'F':73,'G':79,'H':90,'I':80,'J':94,'K':64,'L':84,'M':95,'N':68,'O':49}
for n in mapped:
 b=n['bar'];st=stage(b);p=n['modal_pitch'];q=n['q'];dur=tm(q+n['d'])-tm(q)
 if st=='A' or st=='K' or st=='O':continue
 owner={'B':'sax','C':'suona','D':'suona','E':'oboe','F':'sax','G':'oboe','H':'suona','I':'oboe','J':'suona','L':'sax','M':'suona','N':'sax'}[st]
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
  if st not in ['F']:p-=12
  while p<48:p+=12
  while p>77:p-=12
 elif owner=='oboe':
  p-=12
  while p<58:p+=12
  while p>85:p-=12
 else:
  while p<73:p+=12
  while p>85:p-=12
 on=tm(q)+(0.013 if owner=='sax' else .006)+rng.normal(0,.002)
 add(owner,on,p,dur,levels[st]+(5 if n.get('accent') else 0),b,q=q,phrase=(b-1)//2,accent=n.get('accent',False),source_pitch=n['p'])
# True low-register xiao: newly composed pentatonic answer lines fit this patch's range.
ig=np.array(A['intro_grid']);its=np.array(A['intro_times'])
def im(q):return .35+float(np.interp(q,ig,its))
for i,(q,p,d) in enumerate([(2,56,1),(3.25,59,.6),(6,61,.6),(7,64,.7),(10,61,.6),(11,59,.6),(14,56,1.2),(18,54,.7),(19,56,.7),(22,59,.6),(23,61,.7),(26,64,.7),(27,61,.7),(29,59,.6),(30,56,.7)]):
 add('xiao',im(q),p,im(q+d)-im(q),51+(q>16)*5,0,phrase=int(q//8),program=6)
for b in range(1,121):
 st=stage(b)
 if st in ['A','K','O']:
  pattern=[(0,61,.7),(.9,64,.45),(1.65,61,.6),(2.5,59,.5),(3.2,56,.65)] if b%2 else [(0,56,.8),(1.1,59,.65),(2,61,1.45)]
  if st=='O':pattern=[(0,64 if b%2 else 61,2.3),(2.8,59 if b%2 else 56,.8)]
  for t,p,d in pattern:add('xiao',tm(bb[b]+t),p,tm(bb[b]+t+d)-tm(bb[b]+t),levels[st],b,phrase=(b-1)//2,program=6)
 elif b%2==0 and st in ['C','D','G','H','J','M']:
  for t,p,d in [(2.75,59,.45),(3.35,61,.5)]:add('xiao',tm(bb[b]+t),p,tm(bb[b]+t+d)-tm(bb[b]+t),48,b,phrase=b,program=6)
 # Erhu is a single soft bowed support line, never a lead or impossible chord stack.
 roots=[n for n in out['bass']+out['piano'] if n['bar']==b and n['p']<48]
 if roots:
  pc=roots[0]['p']%12;pad={1:64,4:68,6:64,8:71,11:66}[pc]
  add('erhu',tm(bb[b])+.08,pad,tm(bb[b]+(2 if b==10 else 4))-tm(bb[b])+.12,43 if st not in ['J','M'] else 48,b,phrase=(b-1)//2,program=3)
# Oboe and saxophone connect phrases using only notes of the same gong system.
for b in [18,26,34,46,54,62,70,78,86,94,102,110]:
 q=bb[b]+2.5
 for t,p,d in [(0,76,.4),(.55,73,.55)]:
  if not any(n['bar']==b and n['on']>tm(bb[b]+2) for n in out['oboe']):add('oboe',tm(q+t)+.012,p,tm(q+t+d)-tm(q+t),60,b,phrase=b)
for q,p,d in [(26,73,.6),(27,76,.6),(28.2,78,.7),(29.2,76,.7),(30.2,73,1.1)]:add('oboe',im(q),p,im(q+d)-im(q),56,0,phrase=7)
# A restrained last suona call settles into the yu final, with xiao answering underneath.
for b,t,p,d in [(118,2.0,83,.65),(118,2.9,80,.7),(119,.0,78,.8),(119,1.1,76,.8),(120,0,73,4.2)]:
 add('suona',tm(bb[b]+t),p,tm(bb[b]+t+d)-tm(bb[b]+t),54,b,phrase=60,accent=False)
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
out['mode']=dict(name='C# yu / E gong anhemitonic pentatonic',pitch_classes=sorted(PCS),notes=['C#','E','F#','G#','B'],basis='Existing fusion foundation, rhythm and intro retained; all pitched parts revoiced')
assert all(n['p']%12 in PCS for k in ['xiao','suona','sax','oboe','erhu','guzheng','piano','bass','cello','violins'] for n in out[k])
(R/'arrangement.json').write_text(json.dumps(out,indent=2))
for kind,prog,params in [('xiao',6,{'1':.06,'2':.3,'14':.80,'12':.38,'3':0,'7':.8}),('erhu',3,{'0':.07,'1':.4,'13':.85,'11':.45,'7':0,'5':.8})]:
 ev=[]
 for n in out[kind]:ev.extend([[n['on'],144,n['p'],round(n['v'])],[n['off'],128,n['p'],0]])
 (R/(kind+'_plan.json')).write_text(json.dumps(dict(duration=A['duration'],program=prog,events=sorted(ev),parameters=params),indent=2))
print('MODE',out['mode']['notes'],'NOTES',{k:len(v) for k,v in out.items() if k in ['xiao','suona','sax','oboe','erhu','guzheng','piano','bass','cello','violins']},flush=True)
