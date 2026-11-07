from pathlib import Path
import json,struct,subprocess,shutil,hashlib
import numpy as np
import soundfile as sf
from scipy import signal
import imageio_ffmpeg
W=Path(__file__).resolve().parent;R=W/'dizi_restored';R.mkdir(exist_ok=True)
O=W.parent/'outputs/Dizi_Xiao';(O/'stems').mkdir(parents=True,exist_ok=True)
A=json.loads((W/'xiao/arrangement.json').read_text());old=json.loads((W/'fusion/arrangement.json').read_text())
assert A['duration']==old['duration'] and A['intro_seconds']==old['intro_seconds']
A['xiao']=old['wind']
for p in (O.parent/'Xiao/stems').glob('*.flac'):
 if 'xiao' not in p.name:shutil.copy2(p,O/'stems'/p.name)
source=O.parent/'Fusion/stems/01_dizi_xiao.flac';dest=O/'stems/01_dizi_xiao.flac';shutil.copy2(source,dest)
assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256(dest.read_bytes()).digest()
SR=44100;N=round(A['duration']*SR)
src=(W/'reeds/render_reeds.py').read_text(encoding='utf-8');tail=src[src.index('# Mix a shared, diffused acoustic room.'):];tail=tail[:tail.index('report=dict(')]
tail=tail.replace('One_Last_Kiss_Original_Harmony_Reeds.wav','One_Last_Kiss_Dizi_Xiao.wav')
exec(tail)
report=dict(duration_seconds=len(x)/sr,integrated_lufs=float(st['input_i']),true_peak_dbtp=float(st['input_tp']),clipped_samples=int(np.count_nonzero(abs(x)>=1)),tail_peak_last_second=float(abs(x[-sr:]).max()),restored_lead='Fusion/01_dizi_xiao.flac',restored_lead_bit_identical=True,background_stems_unchanged=True,removed_parts=['sax','oboe','suona'],pentatonic_rewrite=False,manual_listening_verified=False)
assert report['clipped_samples']==0 and report['tail_peak_last_second']<.0001
subprocess.run([ff,'-v','error','-i',str(wav.with_suffix('.mp3')),'-f','null','-'],check=True)
subprocess.run([ff,'-v','error','-y','-ss','53','-i',str(wav),'-t','70','-af','afade=t=in:d=0.2,afade=t=out:st=68:d=2','-b:a','320k',str(O/'Dizi_Xiao_70s_Preview.mp3')],check=True)
# Keep editable MIDI aligned to the restored performance and current foundation.
script=(W/'finish_xiao.py').read_text(encoding='utf-8');midi=script[script.index('def vlq(n):'):script.index("(O/'render_report.json')")]
midi=midi.replace("track(k,ev)","track('dizi_xiao' if k=='xiao' else k,ev)").replace('Xiao_FL_Import.mid','Dizi_Xiao_FL_Import.mid')
exec(midi)
(O/'render_report.json').write_text(json.dumps(report,indent=2));(O/'arrangement.json').write_text(json.dumps(A,indent=2))
(O/'修改说明.txt').write_text('恢复中西合璧 Fusion 版本的原笛箫分轨（逐字节相同），保留当前二胡、古筝、弦乐、低音、钢琴与打击乐铺底。未恢复萨克斯、双簧管或唢呐；未使用五声调式改写。重新混音并保留自然尾响。已检查削波与 MP3 解码，尚未人工试听验收。',encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
