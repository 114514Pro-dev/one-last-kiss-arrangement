from pathlib import Path
import shutil
W=Path(__file__).resolve().parent;R=W/'reeds';R.mkdir(exist_ok=True)
s=(W/'modal/arrange_modal.py').read_text()
s=s.replace('"""C# yu (E gong pentatonic) re-arrangement of the existing acoustic foundation."""','"""Original score melody and harmony with suona, xiao, saxophone and oboe."""')
lo=s.index('# Rewrite every pitched foundation');hi=s.index("mel=R/'source_melody.json'")
s=s[:lo]+'''# Restore the unquantized pitch/harmony foundation; keep the reed-oriented balance.
out={k:copy.deepcopy(A[k]) for k in ['guzheng','piano','bass','cello','violins','percussion']}
out.update(suona=[],xiao=[],sax=[],oboe=[],erhu=[])
for n in out['violins']:
 if n.get('role')=='melody':n['v']-=13
'''+s[hi:]
lo=s.index('# Dynamic programming preserves');hi=s.index('def add(kind,')
s=s[:lo]+"# No pentatonic pitch substitution: use the source melody directly.\nmapped=[dict(n,modal_pitch=n['p']) for n in source]\n"+s[hi:]
s=s.replace("if st=='A' or st=='K' or st=='O':continue","if st=='K' or st=='O' and b>=118:continue")
s=s.replace("owner={'B':'sax'","owner={'A':'oboe','O':'oboe','B':'sax'")
s=s.replace("if st not in ['F']:p-=12","if st not in ['F']:p-=24 if st=='L' and b>=91 else 12")
s=s.replace('while p<73:p+=12\n  while p>85:p-=12','while p<71:p+=12\n  while p>88:p-=12')
lo=s.index('# True low-register xiao');hi=s.index('for b in range(1,121):',lo)
s=s[:lo]+'''# Soft xiao answers use original D#/F# motifs, not a five-note scale restriction.
ig=np.array(A['intro_grid']);its=np.array(A['intro_times'])
def im(q):return .35+float(np.interp(q,ig,its))
for q,p,d in [(2,51,1),(3.25,54,.6),(6,51,.6),(7,54,.7),(10,51,.6),(11,54,.6),(14,51,1.2),(18,59,.7),(19,63,.7),(22,54,.6),(23,51,.7),(26,54,.7),(27,51,.7),(29,54,.6),(30,51,.7)]:
 add('xiao',im(q),p,im(q+d)-im(q),51+(q>16)*5,0,phrase=int(q//8),program=6)
for n in source:
 if 79<=n['bar']<=86:
  add('xiao',tm(n['q']),n['p']-12,tm(n['q']+n['d'])-tm(n['q']),64,n['bar'],phrase=(n['bar']-1)//2,program=6,source_pitch=n['p'])
'''+s[hi:]
lo=s.index(" if st in ['A','K','O']:");hi=s.index(' # Erhu is',lo)
s=s[:lo]+''' if st=='O':
  root=[n for n in out['piano'] if n['bar']==b and n['p']<48]
  pc=root[0]['p']%12 if root else 6
  p={1:63,3:58,4:59,6:54,8:56,11:63}.get(pc,54)
  add('xiao',tm(bb[b])+.05,p,tm(bb[b]+4)-tm(bb[b])-.15,47,b,phrase=(b-1)//2,program=6)
 elif b%2==0 and st in ['C','D','G','H','J','M']:
  for t,p,d in [(2.75,59,.45),(3.35,61,.5)]:add('xiao',tm(bb[b]+t),p,tm(bb[b]+t+d)-tm(bb[b]+t),48,b,phrase=b,program=6)
'''+s[hi:]
s=s.replace("pad={1:64,4:68,6:64,8:71,11:66}[pc]","pad={1:64,3:66,4:68,6:70,8:71,11:75}.get(pc,66)")
s=s.replace("# Oboe and saxophone connect phrases using only notes of the same gong system.","# Responses quote the original D#/C# movement.")
s=s.replace("[(0,76,.4),(.55,73,.55)]","[(0,75,.4),(.55,73,.55)]")
s=s.replace("[(26,73,.6),(27,76,.6),(28.2,78,.7),(29.2,76,.7),(30.2,73,1.1)]","[(26,75,.6),(27,78,.6),(28.2,75,.7),(29.2,78,.7),(30.2,75,1.1)]")
lo=s.index('# A restrained last suona call');hi=s.index("for kind in ['xiao','suona'",lo)
s=s[:lo]+'''# Restore the source ending motif and tied F# final, rather than the added yu cadence.
for n in source:
 if n['bar']>=118:
  add('suona',tm(n['q']),n['p']-12,tm(n['q']+n['d'])-tm(n['q']),54,n['bar'],phrase=60,accent=False,source_pitch=n['p'])
'''+s[hi:]
lo=s.index("out['mode']=");hi=s.index("(R/'arrangement.json')",lo)
s=s[:lo]+'''out['mode']=dict(name='Original score pitch and harmony; no pentatonic quantization',pitch_classes=sorted({n['p']%12 for n in source}),notes=['B','C#','D#','E','F#','G#','A#'],basis='Restore source melody, bass and ending; retain current reed instrumentation and soft xiao')
for kind in ['guzheng','piano','bass','cello','violins']:
 assert [(n['p'],n['on'],n['off']) for n in out[kind]]==[(n['p'],n['on'],n['off']) for n in A[kind]]
for kind in ['suona','sax','oboe']:
 assert all(n['p']%12==n['source_pitch']%12 for n in out[kind] if 'source_pitch' in n)
'''+s[hi:]
(R/'arrange_reeds.py').write_text(s)
for f in ['suona_manifest.json','wind_manifest.json','reed_performances.py']:
 shutil.copy2(W/'modal'/f,R/f)
s=(W/'modal/render_modal.py').read_text().replace("outputs/Modal' if R.name=='modal'","outputs/Reeds' if R.name=='reeds'").replace('One_Last_Kiss_Yu_Mode.wav','One_Last_Kiss_Original_Harmony_Reeds.wav')
s=s.replace("return {'piano':", "return {'suona':W/'modal/samples/suona','sax':W/'modal/samples/sax','oboe':W/'modal/samples/oboe','piano':")
(R/'render_reeds.py').write_text(s)
print('Prepared original-harmony reed project')
