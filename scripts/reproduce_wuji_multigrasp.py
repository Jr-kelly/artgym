"""Reproduce one preregistered arm; creates a new run and never overwrites old runs."""
import argparse,datetime,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',choices=list('ABCD'),required=True);p.add_argument('--gpu',type=int,required=True);p.add_argument('--seed',type=int,default=2026092801);p.add_argument('--epochs',type=int,default=1000);p.add_argument('--name',required=True);a=p.parse_args()
 assert not (R/'runs'/a.name).exists() and not (R/'runs/multigrasp-20260928'/a.name).exists()
 pool='small' if a.arm in 'AC' else 'more';span=.04 if a.arm in 'AB' else .20
 cmd=[sys.executable,'-m','scripts.run_multigrasp_job','--name',a.name,'--gpu',str(a.gpu),'--timeout','21600','--','PYTHON','-m','scripts.train_wuji_multigrasp','task=wuji_multigrasp','hand=wuji_paper_official_actuator','object=knife_wuji_bridge3_20260922','train=wujiAcquisitionSAPG','num_envs=5120','experiment='+a.name,'max_iterations='+str(a.epochs),'multi_gpu=False','headless=True','graphics_device_id=-1','force_render=False','pipeline=gpu','num_subscenes=0','seed='+str(a.seed),'train.params.config.expl_coef_block_size=1024','train.params.config.minibatch_size=32768','train.params.config.save_frequency=250','train.params.config.checkpoint_keep_recent=10','train.params.config.evaluation_frequency=100000','object.reward.GoalDistance2=0.1','task.env.absolutePoseObjective.coefficient=1.0','task.env.supportActionSpan='+str(span),'task.env.trainingStates=research/multigrasp-20260928/data/'+pool+'.npy']
 subprocess.run(cmd,cwd=R,check=True)
if __name__=='__main__':main()
