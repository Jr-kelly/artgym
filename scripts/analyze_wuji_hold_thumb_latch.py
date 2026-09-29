"""Independently verify latch timing, action changes and strict diagnostic scores."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace
from scripts.summarize_wuji_hold_stages import stages,grouped
from scripts.summarize_wuji_multigrasp_trace import summarize

ROOT=Path(__file__).resolve().parents[1]


def main():
    out=ROOT/'research/hold-20260929/analysis-thumb-latch';out.mkdir(parents=True,exist_ok=False)
    results=[]
    for seconds in [2,5]:
        for condition in ['policy','thumb_latch']:
            directory=ROOT/f'runs/hold-20260929/diag-r11-{condition}-fixed{seconds}/evidence'
            saved=json.loads((directory/'report.json').read_text())
            with np.load(directory/'trace.npz') as archive:trace={key:archive[key] for key in archive.files}
            with np.load(directory/'intervention.npz') as archive:control={key:archive[key] for key in archive.files}
            score=score_timed_trace(trace,seconds*30,9,600)
            for key,value in score.items():assert saved[key]==value,(condition,seconds,key)
            assert [x['strict'] for x in summarize(trace,seconds*30)]==[x['stable_full_all_endpoints'] for x in score['records']]
            assert control['latched'].shape==(600,128)
            latch=np.zeros(128,dtype=bool);streak=np.zeros(128,dtype=int)
            for step in range(600):
                changed=np.ones(128,dtype=bool) if step==0 else trace['goal'][step]!=trace['goal'][step-1]
                latch[changed]=False;streak[changed]=0
                if step:
                    valid=trace['active'][step-1]&~trace['fall'][step-1]&~trace['invalid'][step-1]
                    within=(np.abs(trace['slider'][step-1]-trace['goal'][step])<.002)&valid&~changed
                    streak[~within]=0;streak[within]+=1;latch|=streak>=9
                assert np.array_equal(latch,control['latched'][step]),(condition,seconds,step)
            raw=control['raw_action'];sent=control['sent_action'];mask=control['latched']
            assert np.array_equal(raw[:,:,:16],sent[:,:,:16])
            assert np.array_equal(raw[~mask],sent[~mask])
            if condition=='policy':assert np.array_equal(raw,sent)
            else:assert (sent[:,:,16:][mask]==0).all()
            body=(trace['active']&~trace['fall']&~trace['invalid']).all(0)&(trace['drift']<.01).all(0)&(trace['rotation']<.25).all(0)
            results.append(dict(condition=condition,protocol='fixed'+str(seconds),strict=score['stable_full_all_endpoints'],
                alive=score['alive_full'],body_stable=int(body.sum()),n=128,latch_timing_verified=True,action_intervention_verified=True,
                latched_steps=int(mask.sum()),endpoints=grouped(stages(trace,seconds*30)),
                trace_sha256=hashlib.sha256((directory/'trace.npz').read_bytes()).hexdigest(),report=str((directory/'report.json').relative_to(ROOT))))
    report=dict(status='independently_rescored',results=results,
        scope='Same local GPU128 source11 perturbations, scripted thumb increment freeze after observed attainment. Outcome tests this intervention only; does not prove a unique root cause, learned stability, robustness outside this cohort, or hardware applicability.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
