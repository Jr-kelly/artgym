"""Frozen single-push candidate; one command reproduces the continuous simulation."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
D=Path('research/singlepush-20261005')
def selection():
 s=json.loads((D/'FROZEN-CANDIDATE.json').read_text())
 for path,sha in s['required_sha256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha,path
 return s

def command(s,output,no_video=False,load='reference',prepared=None,operation=None,asset=None,resistance=None,options=None):
 c=[sys.executable,'-m','scripts.run_wuji_singlepush','--output',str(output),'--prepared',prepared or s['prepared'],'--operation-prepared',operation or s['operation_prepared'],'--asset',asset or s['asset'],'--resistance',resistance or s['resistance_levels'][load],'--pressure',s['pressure'],'--stroke-m',str(s['stroke_m']),'--checkpoint',s['checkpoint']]
 if s.get('reference_control_config'):c+=['--reference-control-config',s['reference_control_config']]
 if no_video:c+=['--no-video']
 return c+(options or [])
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--no-video',action='store_true');p.add_argument('--load',choices=['reference','1.0','1.25','1.5'],default='reference');a=p.parse_args();subprocess.run(command(selection(),a.output,a.no_video,a.load),check=True)
if __name__=='__main__':main()
