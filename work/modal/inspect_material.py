from pathlib import Path
import re,json
R=Path(__file__).resolve().parent
for file in ['cataudio.html','kong_individual.html']:
 p=R/'sources'/file
 if not p.exists():continue
 txt=p.read_text(encoding='utf-8',errors='replace')
 print(file,[x[:400] for x in txt.splitlines() if any(s in x.lower() for s in ['suona','casn','凌霄'])][:12])
for fn,word in [('VSCO-2-CE','Woodwinds/Oboe'),('VCSL','Tenor Saxophone')]:
 d=json.loads((R.parent/(fn+'.json')).read_text(encoding='utf-8-sig'))
 print(fn,[x['path'] for x in d['tree'] if word in x['path'] and x['type']=='blob'][:8])
