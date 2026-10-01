"""Finite one-geometry static screen and paired frozen manipulation protocols."""
import argparse,json,subprocess,sys
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--static',required=True);p.add_argument('--skip',nargs='*',default=[]);p.add_argument('--split',default='screen-attempts');p.add_argument('--take',type=int,default=16);p.add_argument('--prefix',default='screen-');a=p.parse_args();root=Path('runs/geometry-generalization-20261002');static=root/a.static
 if not (static/'report.json').exists():subprocess.run([sys.executable,'-m','scripts.static_wuji_geometry','--label',a.label,'--split',a.split,'--take',str(a.take),'--output',str(static)],check=True)
 selection=json.loads((static/'selection.json').read_text());assert len(selection['selected_attempt_rows'])>0
 for model in ['teacher','student']:
  for protocol in ['S2','S5','F']:
   if model+'-'+protocol in a.skip:continue
   command=[sys.executable,'-m','scripts.evaluate_wuji_geometry','--label',a.label,'--states',str(static/'valid-states.npy'),'--output',str(root/(a.prefix+a.label+'-'+model+'-'+protocol)),'--model',model,'--protocol',protocol]
   if model=='student' and protocol=='S2' and a.label=='T90':command+=['--fixture']
   subprocess.run(command,check=True)
if __name__=='__main__':main()
