"""Open exactly the frozen90tasks after prefinal optimization and rendering stop."""
import json,os,shlex,subprocess,sys,time
from scripts.record_wuji_width_goal import R,D,record
from scripts.wuji_width_jobs import host_tool_environment,source_hash
from scripts.wuji_width_contract import sha

def run():
    ssh=json.loads(os.environ['WUJI_WIDTH_SSH_ARGV'])
    deadline=time.monotonic()+7200
    frozen=json.loads((D/'final-freeze.json').read_text())
    freeze_sha=sha(D/'final-freeze.json')
    while True:
        s=json.loads((D/'STATE.json').read_text())
        video=[R/v['output']/'geometry-receipt.json' for v in json.loads((D/'VIDEO_PLAN.json').read_text())['entries']]
        if s.get('second_pair_training_complete') and all(p.exists() for p in video) and not s['active_jobs']:break
        assert time.monotonic()<deadline
        time.sleep(10)
    assert not s['final_opened'] and source_hash(R)==frozen['source_sha256'] and sha(D/'final-freeze.json')==freeze_sha
    for v in frozen['models'].values():assert sha(R/v['path'])==v['sha256']
    for v in frozen['cohorts']:
        assert sha(R/v['states'])==v['states_sha256'] and sha(R/v['selection'])==v['selection_sha256']
    # Only research metadata changes. Published job source and assets stay fixed.
    metadata=['final-freeze.json','STATE.json','STATIC_ACCEPTANCE_MANIFEST.json']
    subprocess.run(['rsync','-a','-e',shlex.join(ssh[:-1]),*[str(D/p) for p in metadata],'wangjiarui@10.13.160.5:/tmp/artgym-width-20261002/source/research/width-student-distillation-20261002/'],check=True,timeout=60,env=host_tool_environment())
    record('frozen_final_policy_matrix_opened',evidence='research/width-student-distillation-20261002/final-freeze.json',freeze_sha256=freeze_sha,tasks=90,initial_states=frozen['unique_initial_states'],episodes=frozen['episodes'],state_updates=dict(final_opened=True),next='Run exactly registered sameH200 matrix; no reselection, optimization or grasp/threshold changes')
    log=(D/'frozen-final-controller.log').open('a')
    queue=D/'queues/frozen-final-v1.json'
    subprocess.run([sys.executable,'-m','scripts.wuji_width_queue','run','--queue',str(queue),'--gpus','0','1','2','3','4','5','6','7'],cwd=R,stdout=log,stderr=subprocess.STDOUT,check=True)
    assert all(t['status']=='complete' for t in json.loads(queue.read_text())['tasks'])
    subprocess.run([sys.executable,str(D/'collect_registered_queues.py'),'--queues',str(queue),'--manifest',str(D/'FINAL_MANIFEST.json'),'--output',str(R/'runs/width-student-distillation-20261002/analysis/frozen-final-v1')],cwd=R,check=True)
    record('frozen_final_matrix_independently_rescored',evidence='research/width-student-distillation-20261002/FINAL_MANIFEST.json',state_updates=dict(final_evaluation_complete=True),next='All scientific GPUwork complete; report capabilities and failures, archive and deliver')

if __name__=='__main__':
    try:run()
    except Exception as e:
        record('frozen_final_controller_terminal',failure_type=type(e).__name__,next='Inspect receipts; completed final results immutable, no model changes')
        raise
