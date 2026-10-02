"""Finite first-state video comparison; real rendered resimulations, no selection."""
import json,subprocess,sys,time
from scripts.record_wuji_width_goal import R,D,record

def run():
    deadline=time.monotonic()+6000
    while True:
        q=json.loads((D/'queues/fixed-endpoint-confirm-v1.json').read_text())
        assert not any(t['status']=='failed' for t in q['tasks'])
        if all(t['status']=='complete' for t in q['tasks']):break
        assert time.monotonic()<deadline
        time.sleep(5)
    plan=json.loads((D/'VIDEO_PLAN.json').read_text())
    for v in plan['entries']:
        cmd=['PYTHON','-m','scripts.evaluate_wuji_geometry','--research-dir','research/width-student-distillation-20261002','--label',v['geometry'],'--states',v['state'],'--model','teacher' if v['role']=='teacher' else 'student','--protocol','F','--output',v['output'],'--video']
        if v['role']!='teacher':cmd+=['--student-checkpoint',v['model']]
        name='video-'+v['geometry']+'-'+v['role']+'-first-dev-v1'
        code=subprocess.run([sys.executable,'-m','scripts.wuji_width_jobs','--local','--gpu','0','--seconds','600','--reserved-phase','delivery',name,'--',*cmd],cwd=R).returncode
        record('registered_video_attempt_finished',evidence=v['output'],role=v['role'],geometry=v['geometry'],exit_code=code,next='Preserve this attempt regardless of success; no replacement state')
        if code:break
    record('registered_video_controller_finished',evidence='research/width-student-distillation-20261002/VIDEO_PLAN.json',next='Inspect actual MP4s and raw resimulation scores; keep separate from H200 statistics')

if __name__=='__main__':run()
