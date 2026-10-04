"""Stage this round's explicit public artifacts; private user media excluded."""
import argparse,hashlib,json,os,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/'runs/wrap-force-20261004';D=R/'research/wrap-force-20261004'

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 files=[(B/'release/recovery-v43'/name,name) for name in ['wrap-runtime.tar.gz','wrap-learning-state.tar.gz','wrap-runtime-files.json','wrap-learning-state-files.json','packets.json']]
 files += [(B/'release/evidence-v44'/name,name) for name in ['wrap-curated-evidence.tar.gz','wrap-curated-evidence-files.json']]
 files += [(B/'release/public-v40/Wuji-Wrap-Force-Report.html','Wuji-Wrap-Force-Report.html')]
 files += [(D/name,name) for name in ['FINAL-REPORT.md','REPRODUCE.md','REAL-MEASUREMENT.md','HARDWARE-PREPARATION.md','DELIVERY-RESULTS.json']]
 files += [(B/'media'/name,name) for name in ['new-wrap-corner-nominal-v20.mp4','new-wrap-corner-highload-failure-v20.mp4','paired-original-wrap-held-v31.mp4','paired-original-wrap-held-v31-frame780.png']]
 files += [(B/'train/paired-held-single1-pilot-v1r1/update_000120.pth','selected-S120.pth')]
 files += [(B/'figures/paired-series-repeat-v26'/name,name) for name in ['paired-series-repeat.png','paired-series-repeat.pdf','force-window-results.csv']]
 files += [(B/'figures/recorded-wrap-geometry-v32'/name,name) for name in ['recorded-wrap-geometry.png','recorded-wrap-geometry.pdf']]
 files += [(B/'figures/wide-face-contact-moments-v37'/name,name) for name in ['support-moments.png','support-moments.pdf']]
 rows=[]
 for source,name in files:
  assert source.is_file(),source
  target=a.output/name;shutil.copy2(source,target);rows.append(dict(name=name,source=str(source.relative_to(R)),bytes=target.stat().st_size,sha256=digest(target)))
 manifest=dict(scope=__doc__,assets=rows,selected_actor_sha256='ad16a153c27eb01567c14422ca8ed23e5bebfc6e1c901683031f245631944d2a',sdk_included=False,real_robot_ran=False,archive_state_scope='Source/STATE inside archives is a pre-publication snapshot. Public completion receipt and standalone DELIVERY-RESULTS record publication separately; behavior/force/hardware flags remain distinct.')
 (a.output/'RELEASE-ARTIFACTS.json').write_text(json.dumps(manifest,indent=2)+'\n')
 hashes=rows+[dict(name='RELEASE-ARTIFACTS.json',sha256=digest(a.output/'RELEASE-ARTIFACTS.json'))]
 (a.output/'SHA256SUMS').write_text(''.join(row['sha256']+'  '+row['name']+'\n' for row in hashes));print(json.dumps(dict(assets=len(hashes)+1,total_bytes=sum(x['bytes'] for x in rows),output=str(a.output))))
if __name__=='__main__':main()
