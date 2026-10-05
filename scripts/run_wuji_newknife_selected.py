"""Run the frozen newknife controller as a continuous simulation, never hardware."""
import argparse,json,hashlib,subprocess,sys
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--profile',choices=['constant','variable'],default='constant');p.add_argument('--no-video',action='store_true');a,extra=p.parse_known_args();f=Path('research/newknife-20261005/FROZEN-CANDIDATE.json');selection=json.loads(f.read_text())
 for path,sha in selection['required_sha256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha,path
 cmd=[sys.executable,'-m','scripts.run_wuji_newknife','--output',str(a.output),'--prepared',selection['prepared'],'--asset',selection['asset'],'--pressure',selection['pressure'],'--resistance',selection['profiles'][a.profile]]
 if selection.get('operation_prepared'):cmd+=['--operation-prepared',selection['operation_prepared']]
 cmd+=selection.get('native_options',[])
 if selection.get('trained_checkpoint'):cmd+=['--checkpoint',selection['trained_checkpoint']]
 if a.no_video:cmd+=['--no-video']
 subprocess.run(cmd+extra,check=True)
if __name__=='__main__':main()
