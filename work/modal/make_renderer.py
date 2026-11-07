from pathlib import Path
R=Path(__file__).resolve().parent
s=(R.parent/'fusion/render_fusion.py').read_text()
s=s.replace("outputs/Fusion' if R.name=='fusion'", "outputs/Modal' if R.name=='modal'")
lo=s.index('# Render each fixed native patch');hi=s.index('# Original plucks')
s=s[:lo]+"from reed_performances import render_reeds\nif render:render_reeds(globals())\n"+s[hi:]
for old,new in [("'03_guzheng',buf,-29.0","'06_guzheng',buf,-30.5"),("'07_piano_foundation'","'10_piano_foundation'"),("'06_double_bass'","'09_double_bass'"),("'05_cellos'","'08_cellos'"),("'04_violin_ensemble',-27.0","'07_violin_ensemble',-28.5"),("'08_acoustic_percussion'","'11_acoustic_percussion'"),("'dizi' in p.name or 'erhu' in p.name","any(k in p.name for k in ['xiao','suona','sax','oboe'])"),("ir=rng.standard_normal","ir=np.random.default_rng(82451).standard_normal"),("One_Last_Kiss_Fusion.wav","One_Last_Kiss_Yu_Mode.wav"),("['wind','erhu','guzheng','bass','cello','violins','piano']","['xiao','suona','sax','oboe','erhu','guzheng','bass','cello','violins','piano']"),("score_end=A['score_end'],stems=metrics","score_end=A['score_end'],mode=A['mode'],stems=metrics")]:
 assert old in s,old;s=s.replace(old,new)
(R/'render_modal.py').write_text(s)
