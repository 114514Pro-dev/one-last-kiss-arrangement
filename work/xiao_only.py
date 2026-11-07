from pathlib import Path
import json,copy,shutil
import numpy as np
W=Path(__file__).resolve().parent;R=W/'xiao';R.mkdir(exist_ok=True);O=W.parent/'outputs/Xiao';(O/'stems').mkdir(parents=True,exist_ok=True)
a=json.loads((W/'reeds/arrangement.json').read_text());source=json.loads((W/'guofeng/arrangement.json').read_text())['melody']
g=np.array(a['grid']);s=np.array(a['seconds'])
def tm(q):return a['intro_seconds']+float(np.interp(q,g,s))
notes=[copy.deepcopy(n) for n in a['xiao'] if n['bar']==0]
for n in source:
 b=n['bar']
 if 39<=b<=46 or 65<=b<=70 or 87<=b<=94:continue
 shift=36 if 71<=b<=77 or b>=118 else (12 if 79<=b<=86 else 24)
 p=n['p']-shift
 if p<47:p+=12
 on=tm(n['q'])+.005;off=tm(n['q']+n['d'])
 notes.append(dict(on=on,off=max(on+.07,off),p=p,v=72 if b<111 else 50,bar=b,source_pitch=n['p'],phrase=(b-1)//2))
notes.sort(key=lambda n:n['on'])
for i,n in enumerate(notes[:-1]):
 nxt=notes[i+1]
 if n['phrase']!=nxt['phrase']:n['off']=min(n['off'],nxt['on']-.16)
 elif n['p']==nxt['p']:n['off']=min(n['off'],nxt['on']-.014)
 n['off']=max(n['off'],n['on']+.06)
a['xiao']=notes;a['suona']=[];a['sax']=[];a['oboe']=[]
(R/'arrangement.json').write_text(json.dumps(a,indent=2));ev=[]
for n in notes:ev.extend([[n['on'],144,int(n['p']),int(n['v'])],[n['off'],128,int(n['p']),0]])
(R/'plan.json').write_text(json.dumps(dict(duration=a['duration'],events=sorted(ev),program=6,parameters={'1':.025,'2':.3,'14':.8,'12':.38,'3':0,'7':.85}),indent=2))
for p in (O.parent/'Reeds/stems').glob('*.flac'):
 if not any(k in p.name for k in ['suona','xiao','sax','oboe']):shutil.copy2(p,O/'stems'/p.name)
print('Xiao notes',len(notes),'range',min(n['p'] for n in notes),max(n['p'] for n in notes))
