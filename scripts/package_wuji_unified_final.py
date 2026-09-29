"""Archive immutable final traces per model, keeping each release asset bounded."""
import json,subprocess,sys
from scripts.package_wuji_unified_completed import event,B,D,R

def main():
 for sec in [2,5]:assert (B/f'final-t{sec}/completed.json').exists()
 groups={}
 for model in ['historical','source3','single_historical','single_source3','unified']:
  groups['final-'+model.replace('_','-')]=[B/f'final-t{sec}'/model for sec in [2,5]]
 groups['final-records']=[B/f'final-t{sec}-job' for sec in [2,5]]+[B/'final-launched.json',B/'remote-gpu-release-observation.json']
 for sec in [2,5]:groups['final-records'] += [p for p in (B/f'final-t{sec}').iterdir() if p.is_file()]+[B/f'final-t{sec}-wrapper.log']
 for suffix,items in groups.items():
  name='wuji-unified-'+suffix
  if (D/(name+'.receipt.json')).exists():continue
  paths=[str(p.relative_to(R)) for p in items];event('archive_started',name=name,paths=paths,next='Retain complete frozen final evidence')
  subprocess.run([sys.executable,'-m','scripts.archive_wuji_unified','--name',name,'--paths',*paths],check=True,cwd=R)
  receipt=json.loads((D/(name+'.receipt.json')).read_text());assert receipt['size']<2_000_000_000
  event('archive_completed',**receipt,next='Server digest verify and selected archive public download recovery')
if __name__=='__main__':main()
