"""Chinese/Western acoustic ensemble, source score plus 8-bar motif-based prelude."""
from pathlib import Path
import numpy as np,json,copy
R=Path(__file__).resolve().parent;W=R.parent
src=R/'score_events.json'
if not src.exists():src=W/'score_events.json'
score=json.loads(src.read_text());events=score['events']
old=R/'previous_melody.json'
if not old.exists():old=W/'guofeng/arrangement.json'
melody=json.loads(old.read_text())['melody']
bb={b:next(e['beat']-e['t'] for e in events if e['bar']==b) for b in range(1,121)}
grid=np.arange(0,score['beats']+28,.03125);tempo=np.full(len(grid),112.)
for b in range(1,121):
 mask=(grid>=bb[b])&(grid<bb[b]+(2 if b==10 else 4))
 if b<=10:tempo[mask]=110
 if b in [9,10,18,26,34,46,54,62,70,78,86,102,110]:tempo[mask]*=np.linspace(1,.97,mask.sum())
 if b>=111:tempo[mask]=np.interp(b,[111,115,118,119,120],[105,101,96,86,66])
tempo[grid>=bb[120]+2]=58
sec=np.r_[0,np.cumsum(60/tempo[:-1]*np.diff(grid))]
ig=np.arange(0,32+.03125,.03125);it=np.interp(ig,[0,8,16,24,32],[85,88,96,104,110]);ist=np.r_[0,np.cumsum(60/it[:-1]*np.diff(ig))]
INTRO=float(ist[-1])+.55
def tm(q):return float(np.interp(q,grid,sec))+INTRO
def im(q):return .35+float(np.interp(q,ig,ist))
def stage(b):return next(l for l,a,z in [('A',1,10),('B',11,18),('C',19,26),('D',27,34),('E',35,38),('F',39,46),('G',47,54),('H',55,62),('I',63,70),('J',71,78),('K',79,86),('L',87,94),('M',95,102),('N',103,110),('O',111,120)] if a<=b<=z)
rng=np.random.default_rng(62741)
levels={'A':55,'B':76,'C':88,'D':94,'E':61,'F':74,'G':90,'H':97,'I':82,'J':105,'K':67,'L':86,'M':106,'N':69,'O':50}
out={k:[] for k in ['wind','erhu','guzheng','piano','bass','cello','violins','percussion']}
def add(k,on,p,d,v=75,bar=0,**kw):
 n=dict(on=float(on),off=float(on+d),p=int(p),v=float(v),bar=bar,**kw);out[k].append(n);return n
# First merge per-pitch ties. This also keeps tied accompaniment ringing.
flat=[];active={}
for e in sorted(events,key=lambda e:e['beat']):
 for p in e['p']:
  key=e['hand'],p;pr=active.get(key)
  if e.get('tie') in ['continue','stop'] and pr and abs(pr['q']+pr['d']-e['beat'])<.01:
   pr['d']+=e['d'];continue
  n=dict(q=e['beat'],d=e['d'],p=p,bar=e['bar'],hand=e['hand'],accent=e.get('accent',False));flat.append(n);active[key]=n
# Add an eight-bar prelude around the source's C#m7/E/F#6/D#m7 loop.
intro_chords=[[37,52,56,59,63],[40,56,59,63,66],[42,54,58,61,63],[39,54,58,61],
              [37,52,56,59,63],[40,56,59,63,66],[42,54,58,61,63],[39,54,58,61]]
for i,ch in enumerate(intro_chords):
 q=i*4;on=im(q);end=im(q+4)
 add('piano',on,ch[0],end-on+1.1,48 if i<4 else 55,hold=True)
 for j,p in enumerate(ch[1:]):add('piano',on+.09+j*.035,p,2.8,42+i,hold=True)
 for j,t in enumerate([.7,1.45,2.35,3.15]):
  p=ch[1+j%len(ch[1:])]+12
  add('guzheng',im(q+t),p,2.6,51+i*1.4,natural=True)
 if i>=2:add('cello',on+.05,ch[0]+12,end-on+.22,46+i*2,role='intro')
 if i>=4:
  for p in ch[1:3]:add('violins',on+.09,p+12,end-on+.25,45+(i-4)*3,role='intro')
intro_motif=[(8.5,75,.55),(9.35,78,.35),(9.85,75,.7),(11,78,.5),(11.7,75,1.1),
             (20.4,71,.6),(21.3,75,.6),(22.3,78,.7),(24.2,78,.45),(24.8,80,.8),
             (26.1,80,.35),(26.55,75,.75),(27.5,73,.8),(29,75,.6),(30,78,.5),(30.8,75,.65)]
for q,p,d in intro_motif:add('wind',im(q),p,im(q+d)-im(q),53+(q>20)*8,program=0,phrase=int(q//8),q=-32+q)
# Theme leads are handed over by complete phrases, not by isolated note ranges.
for n in melody:
 b=n['bar'];st=stage(b);q=n['q'];p=n['p'];d=tm(q+n['d'])-tm(q)
 if st in ['F','L'] or st=='I' and b>=65:continue
 owner='wind'
 if st=='C' and b>=23 or st=='G' and b<=50 or st=='H' and b>=59 or st=='J' and 75<=b<=77 or st=='M' or st=='N' and b<=104:owner='erhu'
 if st=='J':p-=12
 if owner=='erhu':p-=12
 if owner=='wind' and st=='K':p-=12
 if st=='O' and b>=118:p-=12
 if b==78:p=n['p']-12
 v=levels[st]+(6 if n.get('accent') else 0)+rng.normal(0,2)
 program=3 if owner=='erhu' else (6 if st=='K' or b==78 else 0)
 if owner=='wind' and st=='J' and b!=78:program=7
 # Short high notes use the actual treble register, avoiding holes in mini patches.
 if owner=='wind' and st in ['D','H'] and d<.28:program=3 if p<83 else 7
 on=tm(q)+(0.013 if owner=='erhu' else .004)+rng.normal(0,.0018)
 add(owner,on,p,d,float(np.clip(v,35,113)),b,program=program,q=q,phrase=(b-1)//2,accent=n.get('accent',False))
 # A real Western string recording adds body underneath the solo timbre.
 if st in ['C','D','G','H','J','M'] and d>=.22:
  sp=p if owner=='erhu' else p-12
  add('violins',on+.024,sp,d+.10,v-15,b,role='melody')
  if d>=.7:add('cello',on+.035,sp-12,d+.16,v-21,b,role='melody')
# Deliberate breath at alternate bar endings, and actual overlap only for different pitches.
for owner in ['wind','erhu']:
 ns=sorted(out[owner],key=lambda n:n['on'])
 for i,n in enumerate(ns):
  nxt=ns[i+1] if i+1<len(ns) else None
  if owner=='wind':
   if nxt and nxt['phrase']!=n['phrase']:
    n['off']=min(n['off'],nxt['on']-.18)
   elif nxt and nxt['on']-n['off']<.08:
    n['off']=min(n['off']+.018,nxt['on']+.012)
   if n.get('accent') and n['off']-n['on']<.3:n['off']-=.025
  else:
   if nxt and nxt['on']-n['off']<.06:n['off']=min(n['off']+.028,nxt['on']+.025)
  if nxt and nxt['p']==n['p']:n['off']=min(n['off'],nxt['on']-.014)
  n['off']=max(n['off'],n['on']+.060)
 out[owner]=ns
# Guzheng: let single plucks decay; tied notes are already merged above.
floors={'A':71,'B':71,'C':78,'D':80,'E':71,'F':59,'G':78,'H':80,'I':71,'J':90,'K':71,'L':75,'M':80,'N':78,'O':71}
for n in flat:
 b=n['bar'];st=stage(b);p=n['p'];q=n['q'];d=tm(q+n['d'])-tm(q)
 if n['hand']==1:
  if p<48:continue
  if st=='O' and n['d']>=4 and p<54:continue
 else:
  dense=st in ['F','I','L','M']
  if not dense and p>=floors[st]:continue
  if st=='J':continue
  if st in ['L','M'] or st=='I' and b>=65:p-=12
 while p<48:p+=12
 while p>84:p-=12
 add('guzheng',tm(q)+rng.normal(0,.003)+((p%3)*.006),p,d,levels[st]-(18 if n['hand']==1 else 10)+7*n['accent'],b,natural=True,accent=n['accent'])
# Same source harmony supports a full acoustic low end and open string voicings.
for b in range(1,121):
 st=stage(b);q=bb[b];qlen=2 if b==10 else 4;on=tm(q);end=tm(q+qlen)
 source=[n for n in flat if n['hand']==1 and n['bar']==b and abs(n['q']-q)<.05]
 if not source:continue
 ps=sorted({n['p'] for n in source});r=min(ps)
 while r<24:r+=12
 while r>47:r-=12
 second=[n for n in flat if n['hand']==1 and n['q']<=q+2.01 and n['q']+n['d']>q+2.02]
 ps2=sorted({n['p'] for n in second}) or ps;r2=min(ps2)
 while r2<24:r2+=12
 while r2>47:r2-=12
 v=levels[st]
 add('piano',on,r,end-on+.9,v-18,b,hold=True)
 if b>=19 and st!='O':add('piano',tm(q+2),r2,min(2,end-tm(q+2))+.7,v-27,b,hold=True)
 if st in ['C','D','G','H','J','L','M']:
  # Do not put major/minor thirds into the very low bass register.
  for j,p in enumerate(sorted({p%12+48 for p in ps if p>r})[:3]):
   add('piano',on+.018*j,p,end-on+.5,v-29,b,hold=True)
 cr=r+12
 while cr<43:cr+=12
 while cr>59:cr-=12
 change=r2!=r and qlen>2
 add('cello',on+.02,cr,(tm(q+2)-on if change else end-on)+.24,v-16,b,role='root')
 if change:
  cr2=r2+12
  while cr2<43:cr2+=12
  while cr2>59:cr2-=12
  add('cello',tm(q+2)+.02,cr2,end-tm(q+2)+.24,v-16,b,role='root')
 if b>=11 and st not in ['E','O']:
  br=r
  while br<31:br+=12
  while br>47:br-=12
  for t,vg in [(0,1),(2,.87)]:
   if qlen==2 and t==2:continue
   br2=br
   if t==2:
    br2=r2
    while br2<31:br2+=12
    while br2>47:br2-=12
   add('bass',tm(q+t)+.007,br2,.95 if st in ['D','F','H','M'] else 1.5,(v-12)*vg,b)
  if st in ['D','F','H','M']:add('bass',tm(q+3.5),br+7,.45,v-28,b)
 if st in ['C','G','I','J','L','M','N','O']:
  chord=sorted({p%12+60 for p in ps})
  # Use 3 voices in middle registers, leaving space for the flute and erhu.
  for j,p in enumerate(chord[:3]):add('violins',on+.045+j*.008,p,(tm(q+2)-on if change else end-on)+.20,v-25,b,role='harmony')
  if change:
   for j,p in enumerate(sorted({p%12+60 for p in ps2})[:3]):add('violins',tm(q+2)+.045+j*.008,p,end-tm(q+2)+.2,v-25,b,role='harmony')
# Phrase-closing guzheng arpeggios quote chord tones only; no foreign-key fill.
for b in [18,26,34,46,54,62,70,78,86,94,102,110]:
 q=bb[b];src=[n for n in flat if n['hand']==1 and n['bar']==b];pcs=sorted({n['p']%12 for n in src})
 for j,pc in enumerate(pcs[:4]):add('guzheng',tm(q+3+j*.17),pc+60,2.3,48+j*2,b,natural=True)
# Low drums, wood and gong remain acoustic, with measured restraint in the intro.
for b in range(11,111):
 st=stage(b);q=bb[b]
 if st=='E':continue
 strong=st in ['D','H','I','L','M'];g=1 if strong else .66
 if st=='N':g=.35
 for t in [0,2]:out['percussion'].append(dict(on=tm(q+t),kind='lowdrum',gain=g,bar=b))
 for t in ([.75,1.5,2.75,3.5] if strong else [1.5,3.5]):out['percussion'].append(dict(on=tm(q+t),kind='wood',gain=.45*g,bar=b))
 if b in [19,47,71,95]:out['percussion'].append(dict(on=tm(q),kind='gong',gain=.15 if b!=95 else .22,bar=b))
 if strong and b%4==2:
  for j in range(4):out['percussion'].append(dict(on=tm(q+3+j*.25),kind='frame',gain=.15+j*.02,bar=b))
# Keep the fermata, give the last breath a gradual finish, and leave ten seconds of room.
end_score=tm(score['beats'])
for k in ['wind','erhu','violins','cello','piano']:
 for n in out[k]:
  if n['bar']==120:n['off']+=1.6
duration=end_score+12
out.update(duration=duration,intro_seconds=INTRO,score_end=end_score,barbeat=bb,grid=grid.tolist(),seconds=sec.tolist(),intro_grid=ig.tolist(),intro_times=ist.tolist())
(R/'arrangement.json').write_text(json.dumps(out,indent=2))
# Each acoustic patch is rendered independently, so patch changes cannot cut old tails.
plans=[]
for kind in ['wind','erhu']:
 for program in sorted({n['program'] for n in out[kind]}):
  notes=[n for n in out[kind] if n['program']==program];ev=[]
  for n in notes:ev.extend([[n['on'],144,n['p'],int(np.clip(n['v'],30,116))],[n['off'],128,n['p'],0]])
  pars={'1':.025,'2':.25,'14':.8,'12':.4,'3':0,'7':.85} if kind=='wind' else {'0':.035,'1':.4,'13':.85,'11':.45,'7':0,'5':.85}
  name=f'{kind}_{program}';(R/(name+'.json')).write_text(json.dumps(dict(duration=duration,events=sorted(ev),program=program,parameters=pars),indent=2));plans.append(dict(name=name,kind=kind,program=program,notes=len(notes)))
(R/'native_plans.json').write_text(json.dumps(plans,indent=2))
print('Prelude',round(INTRO,2),'seconds; duration',round(duration,2),'Notes',{k:len(v) for k,v in out.items() if isinstance(v,list) and k not in ['grid','seconds','intro_grid','intro_times']},flush=True)
