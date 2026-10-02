"""Create C/G manifests from recorded static selections, never policy outcomes."""
import argparse
import json
from pathlib import Path
import numpy as np
from scripts.wuji_width_contract import ROUND, sha, slots
from scripts.record_wuji_width_goal import R, D, record


def main():
    p=argparse.ArgumentParser();p.add_argument('--static-root',type=Path,default=R/'runs'/ROUND/'static')
    a=p.parse_args();data=json.loads((D/'DATA.json').read_text());accepted={}
    for label in ['baseline','W110','W120']:
        directory=a.static_root/(label+'-train')
        selection=json.loads((directory/'selection.json').read_text())
        report=json.loads((directory/'report.json').read_text())
        states=np.load(directory/'valid-states.npy',allow_pickle=False)
        source=np.asarray(selection['source_order'])
        entry=next(e for e in data['entries'] if e['label']==label and e['split']=='train')
        assert report['initial_states_sha256']==entry['sha256']
        assert selection['no_policy_filter'] is True
        assert len(states)==len(source)==len(selection['selected_attempt_rows'])
        original=np.load(R/entry['path'],allow_pickle=False)
        assert np.array_equal(states,original[selection['selected_attempt_rows']])
        for s in range(4):
            rows=states[source==s]
            # Widthsource2 remains evaluation-only. All required source pools
            # must be actual static-valid rows; missing pools block training.
            if label!='baseline' and s==2:continue
            assert len(rows)>0,(label,s,'no valid training data')
            dest=D/'data'/label/('train-valid-source%d.npy'%s)
            assert not dest.exists()
            np.save(dest,rows)
            accepted[(label,s)]=dict(states=str(dest.relative_to(R)),sha256=sha(dest),n=len(rows),
                                     selection=str((directory/'selection.json').relative_to(R)))
    for arm in ['C','G']:
        pools=[]
        for group in range(3):
            label=['baseline','W110','W120'][group] if arm=='G' else 'baseline'
            for source in ([0,1,2,3] if group==0 else [0,1,3]):
                pools.append(dict(group=group,source=source,geometry=label,**accepted[(label,source)]))
        manifest=dict(round=ROUND,arm=arm,statically_validated=True,slots=slots(arm),pools=pools,
                      asset_files=data['packed_asset_files'],policy_success_filter=False,
                      sampler='fixed slots; torch.randint per group/source; restored torch RNG; cumulative counters in checkpoint')
        (D/'data'/(arm+'-training.json')).write_text(json.dumps(manifest,indent=2)+'\n')
    record('static_accepted_training_pools_registered',evidence=['research/'+ROUND+'/data/C-training.json','research/'+ROUND+'/data/G-training.json'],
           state_updates=dict(training_pools_ready=True),next='Same-H200 zero-change and disposable optimizer precheck, measured throughput, formal matched-window registration')


if __name__=='__main__':main()
