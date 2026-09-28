"""Bounded queue for selected-checkpoint tests after matched-budget evaluation."""
import datetime,json,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[1]
B=R/'runs/multigrasp-20260928'
def main():
    deadline=datetime.datetime(2026,9,29,0,30,tzinfo=datetime.timezone.utc)
    while datetime.datetime.now(datetime.timezone.utc)<deadline:
        p=B/'final1000-v1/results.json'
        if p.exists() and json.loads(p.read_text()).get('status')=='completed':break
        time.sleep(20)
    else:raise TimeoutError('Final1000 results not completed by selected evaluation deadline')
    subprocess.run([sys.executable,'-m','scripts.evaluate_wuji_multigrasp_frozen',
        '--states','research/multigrasp-20260928/data/final-cohort-v1/states.npy',
        '--manifest','research/multigrasp-20260928/data/final-cohort-v1/manifest.json',
        '--gpu','0','--label','selected-v1','--selection','development'],cwd=R,check=True,timeout=7200)
if __name__=='__main__':main()
