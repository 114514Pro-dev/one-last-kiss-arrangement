import json,re,concurrent.futures,urllib.request,time
from pathlib import Path
root=Path(__file__).resolve().parent
jobs=[]
for repo in ['SalamanderGrandPiano','VSCO-2-CE']:
    tree=json.loads((root/(repo+'.json')).read_text(encoding='utf-8-sig'))['tree']
    for f in tree:
        p=f['path']; take=False
        if repo=='SalamanderGrandPiano':
            m=re.fullmatch(r'Samples/([A-G]#?\d)v(\d+)\.flac',p)
            take=bool(m and int(m[2]) in [3,7,11,15]) or p.lower().endswith(('.md','.txt')) and '/' not in p
        else:
            take=p.endswith('.wav') and any(s in p for s in ['Strings/Solo Contrabass/Pizz/','Strings/Violin Section/susVib/','Strings/Cello Section/susvib/','Strings/Harp/','VSCO 1 Percussion/drums/bass/','VSCO 1 Percussion/drums/snare/drum1/','VSCO 1 Percussion/varWood/Camo','VSCO 1 Percussion/varMetal/Cymbals/susp/'])
            take=take or ('license' in p.lower() or p.lower()=='readme.md')
        if take and f['type']=='blob': jobs.append((repo,p,f.get('size',0)))
def get(job):
    repo,p,size=job; dst=root/'samples'/repo/p
    if dst.exists() and dst.stat().st_size==size:return
    dst.parent.mkdir(parents=True,exist_ok=True)
    url='https://raw.githubusercontent.com/'+('sfzinstruments/' if repo=='SalamanderGrandPiano' else 'sgossner/')+repo+'/master/'+urllib.parse.quote(p)
    for attempt in range(4):
        try:urllib.request.urlretrieve(url,dst);return
        except Exception:
            if attempt==3:raise
            time.sleep(1)
print('Downloading',len(jobs),'files',round(sum(j[2] for j in jobs)/1e6),'MB',flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    for i,_ in enumerate(ex.map(get,jobs)):
        if i%25==0:print(i,'/',len(jobs),flush=True)
(root/'sample_manifest.json').write_text(json.dumps(jobs,indent=2))
print('DONE',flush=True)
