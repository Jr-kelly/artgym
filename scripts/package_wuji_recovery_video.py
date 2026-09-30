"""Four fixed-source panels, independently checked against their own physical trace."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import numpy as np
import imageio.v2 as imageio
import imageio_ffmpeg
from scripts.wuji_timed_command_metrics import score_timed_trace

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--example',choices=['fixed','failure'],default='fixed');a=p.parse_args()
    root=Path(__file__).resolve().parents[1];frozen=json.loads((root/'research/artmanip-recovery-20260930/final-freeze.json').read_text())
    selected=frozen['video']['rows'] if a.example=='fixed' else frozen['video']['failure_example']['rows']
    r=json.loads((a.input/'report.json').read_text());assert r['initial_state_rows']==selected and len(r['records'])==4
    assert r['checkpoint_sha256']==frozen['models'][frozen['overall_candidate']]['sha256']
    assert r['control_mode']=='privileged_teacher' and not r['student_sha256']
    with np.load(a.input/'trace.npz') as z:t={k:z[k] for k in z.files}
    valid=t['active']&~t['fall']&~t['invalid'];body=valid.all(0)&(t['drift']<.01).all(0)&(t['rotation']<.25).all(0)
    kind=r['protocol']['kind'];steps=600 if kind=='S' else 1200
    assert len(t['active'])==steps,'Video must retain full declared horizon; short all-terminal examples require a separately labelled packaging plan'
    if kind=='S':
        score=score_timed_trace(t,r['protocol']['stage_steps'],9,600);assert score['records']==r['records']
        success=[x['stable_full_all_endpoints'] for x in score['records']]
        descriptor=f"S fixed {r['protocol']['stage_seconds']:g}s commands, strict20s"
    else:
        phase=np.zeros(4,dtype=int);streak=np.zeros(4,dtype=int);cycles=np.zeros(4,dtype=int);initial=t['goal'][0]-.04
        for step in range(steps):
            expected=initial+np.where(phase==0,.04,0)
            assert np.allclose(t['goal'][step][valid[step]],expected[valid[step]],atol=1e-6)
            streak=np.where(valid[step]&(abs(t['slider'][step]-t['goal'][step])<.01),streak+1,0)
            ready=streak>=45;cycles+=ready&(phase==1);phase[ready]=1-phase[ready];streak[ready]=0
        assert cycles.tolist()==[x['cycles'] for x in r['records']]
        success=(cycles>=1).tolist();descriptor='F 40s, arrival10mm + hold1.5s then switch'
    assert not a.output.exists();a.output.parent.mkdir(parents=True,exist_ok=True)
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';cp=r['checkpoint_sha256']
    filters=['[0:v]split=4[v0][v1][v2][v3]','[v0]crop=512:384:0:0[p0]','[v1]crop=512:384:512:0[p1]','[v2]crop=512:384:1024:0[p2]','[v3]crop=512:384:0:384[p3]','[p0][p1][p2][p3]hstack=inputs=4,pad=2048:512:0:64:black[grid]']
    label='fixed examples' if a.example=='fixed' else 'development failure example'
    header=f'SAME WEIGHTS | privileged teacher | {descriptor} | {label} | SHA {cp[:12]}'
    draw=f"[grid]drawtext=fontfile={font}:text='{header}':x=14:y=9:fontsize=23:fontcolor=white,drawtext=fontfile={font}:text='Fixed development examples in simulation. Separate from final batch statistics. No hardware result.':x=14:y=38:fontsize=18:fontcolor=white"
    for source,ok in enumerate(success):
        outcome=('STRICT ' if kind=='S' else 'CYCLE ')+('PASS' if ok else 'FAIL')
        second=f"40s body {'PASS' if body[source] else 'FAIL'} / cycles {cycles[source]}" if kind=='F' else f"20s body {'PASS' if body[source] else 'FAIL'}"
        color='lime' if ok else 'red'
        draw+=f",drawtext=fontfile={font}:text='Source {source} | {outcome}':x={source*512+15}:y=452:fontsize=22:fontcolor={color},drawtext=fontfile={font}:text='{second}':x={source*512+15}:y=483:fontsize=19:fontcolor=white"
    filters.append(draw+'[out]')
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(a.input/'policy.mp4'),'-filter_complex',';'.join(filters),'-map','[out]','-an','-c:v','libx264','-crf','20','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(a.output)],check=True)
    reader=imageio.get_reader(a.output);probe=reader.get_meta_data();count=reader.count_frames();reader.close()
    assert count==steps and abs(float(probe['duration'])-steps/30)<.2
    imageio.imwrite(a.output.with_suffix('.preview.png'),imageio.get_reader(a.output).get_data(steps//2))
    out=dict(video=str(a.output),sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),trace_sha256=hashlib.sha256((a.input/'trace.npz').read_bytes()).hexdigest(),checkpoint_sha256=cp,source_rows=selected,example=a.example,protocol=kind,example_success=success,example_body=body.tolist(),frame_count=count,duration_seconds=steps/30,independent_rescore=True,policy='same privileged teacher weights; no source routing',scope='Fixed development examples, separately simulated; not final cohort statistics or hardware')
    a.output.with_suffix('.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
