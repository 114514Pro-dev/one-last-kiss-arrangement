from pathlib import Path
import music21 as m,json
files=list(Path('work/omr').rglob('*.mxl'))+list(Path('work/omr').rglob('*.musicxml'))
print(files)
if not files:raise SystemExit()
s=m.converter.parse(files[0])
print('PARTS',[(p.id,len(p.getElementsByClass(m.stream.Measure))) for p in s.parts])
for pi,p in enumerate(s.parts):
 print('PART',pi)
 for bar in p.getElementsByClass(m.stream.Measure):
  ns=list(bar.recurse().notes)
  print(bar.number,'off',bar.offset,'dur',bar.duration.quarterLength,'TS',bar.timeSignature,'KEY',bar.keySignature,'DYN',[(x.offset,x.value) for x in bar.recurse().getElementsByClass(m.dynamics.Dynamic)],' '.join(str(n.offset)+':'+','.join(p.nameWithOctave for p in n.pitches)+'/'+str(n.quarterLength)+('~'+str(n.tie.type) if n.tie else '') for n in ns))
