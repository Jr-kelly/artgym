"""Finite owned local camera jobs, with the same launcher budget/concurrency guard."""
import json,subprocess,sys
from pathlib import Path
from scripts.record_wuji_geometry_goal import D,R,record
def main():
 plans=json.loads((D/'VIDEO_PLAN.json').read_text())['plans'];record('paired_camera_queue_started',jobs=2*len(plans),next='Keep actual camera outcomes separate from frozen H200 statistics')
 for p in plans:
  label=p['label'];protocol=p['protocol'];directories=[]
  for model in ['teacher','student']:
   name='video-'+label+'-'+model+'-'+protocol;output='runs/geometry-generalization-20261002/'+name;directories.append(output)
   command=[sys.executable,'-m','scripts.wuji_geometry_jobs','--gpu','0','--seconds','900','--local',name,'--','/home/agiuser/miniconda3/envs/artgym/bin/python','-m','scripts.evaluate_wuji_geometry','--label',label,'--states','research/geometry-generalization-20261002/video-states/'+label+'.npy','--model',model,'--protocol',protocol,'--output',output,'--video']
   subprocess.run(command,check=True)
  env=__import__('os').environ.copy();env.update(LD_LIBRARY_PATH='/home/agiuser/miniconda3/envs/artgym/lib',PYTHONPATH='.:rl_games',PYTHONNOUSERSITE='1',CUDA_VISIBLE_DEVICES='')
  subprocess.run(['/home/agiuser/miniconda3/envs/artgym/bin/python','-m','scripts.package_wuji_geometry_video','--teacher',directories[0],'--student',directories[1],'--output','research/geometry-generalization-20261002/videos/'+label+'-'+protocol+'-paired.mp4','--sources',*[str(x) for x in p['sources']]],check=True,env=env)
 record('paired_camera_queue_completed',next='Verify all video frames/outcome labels and publish previews and camera evidence')
if __name__=='__main__':main()
