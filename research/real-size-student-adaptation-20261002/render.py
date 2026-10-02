import json,subprocess
from scripts.record_wuji_real_size_goal import R,D,record
f=json.loads((D/'freeze.json').read_text())
for label,m in f['models'].items():
 out='runs/real-size-student-adaptation-20261002/video/'+label
 subprocess.run(['python3','-m','scripts.wuji_real_size_jobs','--gpu','0','--seconds','300','--local','--reserved-phase','delivery','video-'+label,'--','PYTHON','-m','scripts.evaluate_wuji_real_size','--states','research/real-size-student-adaptation-20261002/video-state/states.npy','--student-checkpoint',m['path'],'--output',out,'--video'],cwd=R,check=True)
record('threeway_video_raw_completed',evidence='runs/real-size-student-adaptation-20261002/video',next='Compose one labeled comparison; do not count camera resimulations as independent evidence')
