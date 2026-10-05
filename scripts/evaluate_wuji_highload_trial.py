"""Original criterion plus separately labelled extra-cycle diagnostics.

For 46 s recordings, preserve the original full evaluation and additionally
evaluate the required first 36 s with the exact original two-cycle evaluator.
This prefix is not a new independent run; third-cycle failures remain visible.
"""
import argparse,json,shutil
from pathlib import Path
import numpy as np
from scripts.evaluate_wuji_antirotation import evaluate
from scripts.analyze_wuji_highload_cycles import analyze
def main():
    p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);a=p.parse_args();trial=a.trial
    result=evaluate(trial);(trial/'functional-evaluation.json').write_text(json.dumps(result,indent=2))
    cycles=analyze(trial);z=np.load(trial/'trace.npz')
    if z['time'][-1]>36.1:
        folder=trial/'first-two-cycles';folder.mkdir(exist_ok=True)
        for name in ['report.json','plan.json','physics.json']:shutil.copy2(trial/name,folder/name)
        ids=z['time']<=36.001;np.savez_compressed(folder/'trace.npz',**{k:z[k][ids] for k in z.files})
        prefix=evaluate(folder);(folder/'functional-evaluation.json').write_text(json.dumps(prefix,indent=2));cycles['first_two_original_criterion']=prefix;cycles['prefix_scope']='Exact first36s from same longer physical run; not an independent repetition. All third-cycle findings retained.'
    (trial/'cycle-diagnostics.json').write_text(json.dumps(cycles,indent=2));print(json.dumps(dict(trial=str(trial),checks=result['checks'],endpoints_mm={k:v*1000 for k,v in result['slider_endpoints_m'].items()},cycles=cycles['cycles'])))
if __name__=='__main__':main()
