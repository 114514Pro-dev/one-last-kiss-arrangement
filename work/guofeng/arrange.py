from pathlib import Path
import json,copy
import numpy as np
R=Path(__file__).resolve().parent
sf=R/'score_events.json'
if not sf.exists():sf=R.parent/'score_events.json'
score=json.loads(sf.read_text());events=score['events']
barbeat={b:next(e['beat']-e['t'] for e in events if e['bar']==b) for b in range(1,121)}
grid=np.arange(0,score['beats']+20,.03125);tempo=np.full(len(grid),112.)
for b in range(1,121):
 mask=(grid>=barbeat[b])&(grid<barbeat[b]+(2 if b==10 else 4))
 if b<=10:tempo[mask]=110
 if b in [9,10,18,26,34,46,54,62,70,78,86,102,110]:tempo[mask]*=np.linspace(1,.96,mask.sum())
 if b>=111:tempo[mask]=np.interp(b,[111,115,118,119,120],[105,101,96,86,69])
tempo[grid>=barbeat[120]+2]=60;seconds=np.r_[0,np.cumsum(60/tempo[:-1]*np.diff(grid))]
def tm(q):return float(np.interp(q,grid,seconds))+.35
def stage(b):return next(l for l,a,z in [('A',1,10),('B',11,18),('C',19,26),('D',27,34),('E',35,38),('F',39,46),('G',47,54),('H',55,62),('I',63,70),('J',71,78),('K',79,86),('L',87,94),('M',95,102),('N',103,110),('O',111,120)] if a<=b<=z)
floor={'A':71,'B':71,'C':78,'D':80,'E':71,'F':59,'G':78,'H':80,'I':71,'J':90,'K':71,'L':75,'M':80,'N':78,'O':71}
rng=np.random.default_rng(20261106)
# Read the melody above the pianistic inner voice. Ties merge before assignment.
heads=[];active={}
for e in sorted([e for e in events if e['hand']==0],key=lambda e:e['beat']):
 st=stage(e['bar']);threshold=floor[st]
 if 65<=e['bar']<=70:threshold=83
 if e['bar']==78:threshold=68
 for p in e['p']:
  if p<threshold:continue
  prev=active.get(p)
  if e.get('tie') in ['stop','continue'] and prev and abs(prev['q']+prev['d']-e['beat'])<.01:
   prev['d']+=e['d'];continue
  n=dict(q=e['beat'],d=e['d'],p=p,bar=e['bar'],accent=e.get('accent',False));heads.append(n);active[p]=n
groups={}
for n in heads:
 old=groups.get(n['q'])
 if not old or n['p']>old['p'] or n['p']==old['p'] and n['d']>old['d']:groups[n['q']]=n
melody=[]
for n in sorted(groups.values(),key=lambda n:n['q']):
 if melody:
  prev=melody[-1]
  if prev['q']+prev['d']>n['q']+.01 and n['p']<prev['p']:continue
  prev['d']=min(prev['d'],n['q']-prev['q'])
 melody.append(copy.deepcopy(n))
# Long phrase leads move between xiao, dizi and erhu. Plucked passages stay plucked.
wind=[];erhu=[];guz=[];piano=[]
lev={'A':58,'B':76,'C':87,'D':93,'E':58,'F':74,'G':88,'H':96,'I':80,'J':104,'K':69,'L':78,'M':105,'N':66,'O':48}
for n in melody:
 b=n['bar'];st=stage(b);q=n['q'];p=n['p'];dur=tm(q+n['d'])-tm(q)
 if st in ['F','L'] or st=='I' and b>=65:continue
 instrument='erhu' if st in ['C','G','M'] else 'wind'
 if st=='D' and b>=31:instrument='erhu'
 if st=='N' and b<=104:instrument='erhu'
 if st=='J':p-=12
 if instrument=='erhu':
  p-=12
  while p>83:p-=12
  while p<57:p+=12
  program=3
 else:
  program=6 if st=='K' else (7 if st=='J' else 0)
  if st in ['D','H'] and dur<.35:program=3 if p<83 else 7
  if program in [5,6]:
   p-=12
   while p>76:p-=12
   while p<55:p+=12
  else:
   if st=='O' and b>=118:p-=12
   while p>91:p-=12
   while p<60:p+=12
  if b==78:program=6
 # End phrases with space for an inhalation or bow change, retaining the beat.
 gate=1.015 if instrument=='erhu' else .96
 if n['accent'] and n['d']<=.5:gate=.74
 if n['d']>=1.5 and instrument=='wind':gate=.88
 on=tm(q)+(.012 if instrument=='erhu' else .004)+rng.normal(0,.0025)
 off=on+max(.055,dur*gate)
 vel=int(np.clip(lev[st]+(7 if n['accent'] else 0)+rng.normal(0,3),35,115))
 item=dict(on=float(on),off=float(off),p=p,v=vel,program=program,bar=b,source_pitch=n['p'])
 (erhu if instrument=='erhu' else wind).append(item)
# Erhu answers cadences using existing melodic tones, leaving room around the dizi.
for b in [18,26,34,54,62,70,78,86,94,110]:
 candidates=[n for n in melody if n['bar']==b]
 if not candidates:continue
 n=candidates[-1];p=n['p']
 while p>80:p-=12
 while p<57:p+=12
 if any(x['bar']==b for x in erhu):continue
 on=tm(n['q']);erhu.append(dict(on=on+.015,off=on+min(1.1,tm(n['q']+n['d'])-on),p=p,v=64,program=3,bar=b,source_pitch=n['p']))
# Guzheng assumes the rhythmic work; retain the original pitches in useful registers.
for e in events:
 b=e['bar'];st=stage(b);ps=e['p'][:]
 if e['hand']==1:
  if e['t']==0 and e['d']>=2:ps=ps[-3:]
  else:ps=[p for p in ps if p>=47][-3:]
  if st=='O':ps=ps[-2:]
 else:
  dense=st in ['F','I','L','M']
  ps=[p for p in ps if dense or p<floor[st]]
  if st=='A' and e['bar']<=3:ps=e['p']
  if st=='N':ps=ps[-2:]
 if not ps:continue
 if e.get('tie') in ['stop','continue']:continue
 for j,p in enumerate(ps):
  if e['hand']==0 and (st in ['L','M'] or st=='I' and b>=65):p-=12
  while p<48:p+=12
  while p>84:p-=12
  on=tm(e['beat'])+j*.012+rng.normal(0,.003)
  vel=lev[st]-(18 if e['hand']==1 else 8)+(8 if e.get('accent') else 0)
  if st=='L':vel+=2*(b-87)
  if st=='O':vel-=max(0,b-115)*2
  guz.append(dict(on=float(on),p=p,v=int(np.clip(vel+rng.normal(0,3),29,112)),gate=max(.16,min(1.55,(tm(e['beat']+e['d'])-tm(e['beat']))*1.2)),bar=b,accent=e.get('accent',False)))
# Soft tremolo supports long bowed statements without adding a new melody.
for n in erhu:
 if n['off']-n['on']<1.1 or n['bar']>=111:continue
 p=n['p']
 for k,t in enumerate(np.arange(n['on']+.08,n['off']-.07,.105)):
  guz.append(dict(on=float(t),p=p,v=int(45+(k%2)*5),gate=.14,bar=n['bar'],tremolo=True))
# Piano is reduced to root and sparse low harmony, never the lead melody.
for b in range(1,121):
 ns=[e for e in events if e['hand']==1 and e['bar']==b and e['t']<.1]
 if not ns:continue
 ps=sorted({p for e in ns for p in e['p']});root=min(ps)
 while root<29:root+=12
 while root>47:root-=12
 if b==10:continue
 piano.append(dict(on=tm(barbeat[b]),p=root,v=43 if b<111 else 32,gate=1.25,bar=b))
 if stage(b) in ['C','G','J','M']:
  for p in sorted({p%12+48 for p in ps})[:2]:piano.append(dict(on=tm(barbeat[b]+2),p=p,v=34,gate=.8,bar=b))
# Deduplicate overlapping unison plucks in the shared guzheng part.
dedup={}
for n in guz:
 key=(round(n['on']*25),n['p']);old=dedup.get(key)
 if old is None or n['v']>old['v']:dedup[key]=n
guz=sorted(dedup.values(),key=lambda n:n['on'])
duration=tm(score['beats'])+9
for name,notes in [('dizi_xiao',wind),('erhu',erhu)]:
 ev=[];lastprog=None
 for n in sorted(notes,key=lambda n:n['on']):
  if n['program']!=lastprog:ev.append([max(0,n['on']-.025),192,n['program'],0]);lastprog=n['program']
  ev.extend([[n['on'],144,n['p'],n['v']],[n['off'],128,n['p'],0]])
 ev.sort(key=lambda e:(e[0],e[1]))
 params={'3':0.,'7':.85,'12':.16} if name=='dizi_xiao' else {'7':0.,'11':.22,'5':.8}
 (R/(name+'_plan.json')).write_text(json.dumps(dict(duration=duration,events=ev,program=6 if name=='dizi_xiao' else 3,parameters=params),indent=2))
out=dict(duration=duration,barbeat=barbeat,grid=grid.tolist(),seconds=seconds.tolist(),wind=wind,erhu=erhu,guzheng=guz,piano=piano,melody=melody)
(R/'arrangement.json').write_text(json.dumps(out,indent=2))
print('Notes:',{k:len(v) for k,v in [('wind',wind),('erhu',erhu),('guzheng',guz),('piano',piano)]},flush=True)
