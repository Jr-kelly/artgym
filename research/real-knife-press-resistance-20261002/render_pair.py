"""One predeclared paired camera demonstration, using existing rendering path."""
import json,subprocess
from scripts.record_wuji_press_goal import R,D,record
for press,label in [(0,'zero'),(.5,'low')]:
 name='video-variable-'+label;out='runs/real-knife-press-resistance-20261002/video/'+label
 subprocess.run(['python3','-m','scripts.wuji_press_jobs','--gpu','0','--seconds','300','--local','--reserved-phase','delivery',name,'--','PYTHON','-m','scripts.evaluate_wuji_press','--states','research/real-knife-press-resistance-20261002/video-state.npy','--output',out,'--press-mm',str(press),'--resistance-n','.05','--profile','variable','--profile-seed','2026100233','--video'],cwd=R,check=True)
record('one_paired_camera_demonstration_completed',evidence='runs/real-knife-press-resistance-20261002/video',next='Keep actual failures andlabelRTXresimulation separatefromH200statistics; publishonepairedclip')
