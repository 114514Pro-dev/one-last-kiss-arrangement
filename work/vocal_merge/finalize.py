from pathlib import Path
import json,subprocess,shutil,numpy as np,soundfile as sf,imageio_ffmpeg
R=Path(__file__).resolve().parent;W=R.parent;O=W.parent/'outputs/Vocal_Mix';ff=imageio_ffmpeg.get_ffmpeg_exe();a=json.loads((W/'fusion/arrangement.json').read_text());intro=a['intro_seconds'];wav=O/'One_Last_Kiss_Vocal_Dizi_Xiao.wav'
src=(R/'merge.py').read_text(encoding='utf-8')
exec(src[src.index('def measure(p):'):src.index("st=measure(R/'premaster.wav')")])
exec(src[src.index("subprocess.run([ff,'-v','error','-y','-ss','18'"):])
