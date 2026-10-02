"""Prepare final reports only after full frozen matrix independent rescore."""
import json,os,subprocess,time
from scripts.record_wuji_width_goal import R,D,record
end=time.monotonic()+10800
while not json.loads((D/'STATE.json').read_text()).get('final_evaluation_complete'):
 assert time.monotonic()<end
 time.sleep(20)
subprocess.run(['python3',str(D/'summarize_delivery_resources.py')],cwd=R,check=True)
e=os.environ.copy();e.update(PATH='/home/agiuser/miniconda3/envs/artgym/bin:/usr/bin:/bin',LD_LIBRARY_PATH='/home/agiuser/miniconda3/envs/artgym/lib',PYTHONPATH='.:rl_games',PYTHONNOUSERSITE='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',CUDA_VISIBLE_DEVICES='')
subprocess.run(['/home/agiuser/miniconda3/envs/artgym/bin/python',str(D/'make_research_figures.py'),'--final'],cwd=R,env=e,check=True)
subprocess.run(['python3',str(D/'write_final_report.py')],cwd=R,check=True)
record('final_report_ready_for_evidence_review',evidence='research/width-student-distillation-20261002/FINAL_REPORT.md',next='Review final conclusions/plots and publish new finalv2 evidence; no GPU experiments remain')
