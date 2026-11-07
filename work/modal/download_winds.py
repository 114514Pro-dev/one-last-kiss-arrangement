import json,urllib.request,urllib.parse,concurrent.futures,time
from pathlib import Path
R=Path(__file__).resolve().parent
jobs=[]
for fn,repo in [('VSCO-2-CE','sgossner/VSCO-2-CE'),('VCSL','sgossner/VCSL')]:
 tree=json.loads((R.parent/(fn+'.json')).read_text(encoding='utf-8-sig'))['tree']
 for f in tree:
  p=f['path']
  if f['type']!='blob' or not p.lower().endswith(('.wav','.flac','.ogg','.aif','.aiff','.mp3')):continue
  take=p.startswith('Woodwinds/Oboe/') if fn=='VSCO-2-CE' else 'Tenor Saxophone/' in p
  if not take:continue
  sub='oboe' if fn=='VSCO-2-CE' else 'sax'
  dest=R/'samples'/sub/Path(p).name
  jobs.append(dict(url='https://raw.githubusercontent.com/'+repo+'/master/'+urllib.parse.quote(p),path=str(dest.relative_to(R)),source_path=p,size=f.get('size',0),kind=sub,license='CC0'))
def get(j):
 p=R/j['path'];p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists() or p.stat().st_size!=j['size']:
  for retry in range(5):
   try:
    with urllib.request.urlopen(j['url'],timeout=60) as f:content=f.read()
    if len(content)!=j['size']:raise ValueError('incomplete size')
    p.write_bytes(content);break
   except Exception:
    if retry==4:raise
    time.sleep(1+retry)
 return j
print('Download',len(jobs),'files',round(sum(j['size'] for j in jobs)/1e6),'MB',flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
 for i,j in enumerate(ex.map(get,jobs)):
  if i%20==0:print(i,flush=True)
(R/'wind_manifest.json').write_text(json.dumps(jobs,indent=2));print('DONE',flush=True)
