from pathlib import Path
import re,json,html,urllib.request,concurrent.futures,time
R=Path(__file__).resolve().parent
def fetch(url,path):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists() and path.stat().st_size>1000:return path
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
 with urllib.request.urlopen(req,timeout=45) as r:path.write_bytes(r.read())
 return path
manifest=[]
def dizi(page):
 url='https://freesound.org/people/Hypnotriod/packs/21613/'+('?page='+str(page) if page>1 else '')
 p=fetch(url,R/f'sources/dizi_pack{page}.html');text=p.read_text(encoding='utf-8')
 for mp3,title in re.findall(r'data-mp3="([^"]+)".*?data-title="([^"]+)"',text,re.S):
  title=html.unescape(title);m=re.search(r'_(\d+)_([A-G]#?\d)',title)
  if not m:continue
  dest=R/'samples/dizi'/title.replace('.wav','.mp3')
  url=mp3.replace('-lq.mp3','-hq.mp3')
  manifest.append(dict(instrument='dizi',pitch=int(m[1])+12,title=title,path=str(dest.relative_to(R)),url=url,license='CC0',author='Hypnotriod'))
def erhu(kind):
 url='https://remix.berklee.edu/bisa-chinese-erhu-oneshots-'+kind+'/'
 p=fetch(url,R/f'sources/erhu_{kind}.html');text=p.read_text(encoding='utf-8')
 pairs=re.findall(r'href="(https://remix.berklee.edu/context/[^"]+/type/native/viewcontent)"[^>]*title="Download File of ([^"]+)"',text)
 print(kind,len(pairs),flush=True)
 for url,title in pairs:
  title=html.unescape(title);m=re.search(r'\(([A-G][#b]?\d)\)',title)
  if not m:continue
  title=title.split('(audio/')[0].strip();fname=re.sub(r'[^\w#.-]+','_',title)+'.wav';dest=R/'samples/erhu'/kind/fname
  manifest.append(dict(instrument='erhu',note=m[1],articulation=kind,title=title,path=str(dest.relative_to(R)),url=url,license='CC BY',author='Yu Chun Chan / Josefina Ugarte / Asher Deverna; Berklee BISA'))
for page in [1,2]:dizi(page)
for kind in ['vibrato','accented','mercato','harmonic','pizzicato']:
 try:erhu(kind)
 except Exception as e:print('skip',kind,str(e),flush=True)
def get(item):
 try:fetch(item['url'],R/item['path']);return item
 except Exception as e:print('ERR',item['title'],str(e),flush=True);return None
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:got=[x for x in ex.map(get,manifest) if x]
(R/'instrument_manifest.json').write_text(json.dumps(got,ensure_ascii=False,indent=2),encoding='utf-8')
print('GOT',len(got),flush=True)
