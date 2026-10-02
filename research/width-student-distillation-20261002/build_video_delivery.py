"""Factual video labels and comparisons; terminated clips explicitly held."""
import json,subprocess
from pathlib import Path
import imageio,imageio_ffmpeg
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.record_wuji_width_goal import R,D,record
from scripts.analyze_wuji_geometry import read_run
from scripts.wuji_width_contract import sha

def main():
    plan=json.loads((D/'VIDEO_PLAN.json').read_text())
    out=R/'runs/width-student-distillation-20261002/video-delivery';out.mkdir(exist_ok=False)
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    assert Path(font).exists()
    rows=[]
    for v in plan['entries']:
        p=R/v['output'];assert sha(R/v['state'])==v['state_sha256']
        models=dict(teacher=plan['entries'][1]['model_sha256'],student=v['model_sha256'])
        row=read_run(p,dict(source_order=[3],selected_attempt_rows=[v['original_attempt_row']]),models)[0]
        reader=imageio.get_reader(p/'policy.mp4');meta=reader.get_meta_data();count=reader.count_frames();reader.close()
        report=json.loads((p/'report.json').read_text());assert count==report['recorded_steps'] and meta['fps']==30
        name=v['geometry']+'-'+v['role'];caption=out/(name+'.txt');target=out/(name+'-annotated.mp4')
        added={'P':0,'teacher':0,'C':800,'G':800,'C_endpoint':3200,'G_endpoint':3200}[v['role']]
        joint=row['success'] and row['body_stable']
        caption.write_text(name+' | source3 | +'+str(added)+' updates'+(' | MAIN' if v['role']=='C_endpoint' else '')+'\nRTX4090 rendered resimulation; separate from H200 statistics\nF: function='+str(int(row['success']))+' hold='+str(int(row['body_stable']))+' joint='+str(int(joint))+' | duration='+str(count/30)+'s\nFirst registered dev state; no policy-based selection')
        filt='pad=iw:ih+90:0:90:color=black,drawtext=fontfile='+font+':textfile='+str(caption)+':fontsize=12:fontcolor=white:x=8:y=8'
        subprocess.run([ff,'-y','-loglevel','error','-i',str(p/'policy.mp4'),'-vf',filt,'-c:v','libx264','-preset','fast','-crf','20','-threads','2','-an',str(target)],check=True,timeout=180)
        rows.append(dict(**v,metrics=row,raw_video=str((p/'policy.mp4').relative_to(R)),raw_sha256=sha(p/'policy.mp4'),trace_sha256=sha(p/'trace.npz'),annotated=str(target.relative_to(R)),annotated_sha256=sha(target),frames=count,duration_seconds=count/30,terminated_before40=count<1200,first_frame_simulation_time_seconds=1/30,video_not_statistical_evidence=True))
    comparisons=[]
    for geometry in ['baseline','W120']:
        selected=[r for r in rows if r['geometry']==geometry];cmd=[ff,'-y','-loglevel','error']
        for r in selected:cmd+=['-i',str(R/r['annotated'])]
        filters=[]
        for i,r in enumerate(selected):
            filt='[%d:v]tpad=stop_mode=clone:stop_duration=40'%i
            if r['terminated_before40']:
                filt+=",drawtext=fontfile="+font+":text='ENDED - final frame held':fontsize=20:fontcolor=red:box=1:boxcolor=black:x=8:y=h-35:enable='gte(t,"+str(r['duration_seconds'])+")'"
            filters.append(filt+'[v%d]'%i)
        filters.append(''.join('[v%d]'%i for i in range(6))+'xstack=inputs=6:layout=0_0|512_0|1024_0|0_474|512_474|1024_474[out]')
        target=out/(geometry+'-six-model-comparison.mp4')
        subprocess.run(cmd+['-filter_complex',';'.join(filters),'-map','[out]','-t','40','-c:v','libx264','-preset','fast','-crf','20','-threads','2','-an',str(target)],check=True,timeout=240)
        reader=imageio.get_reader(target);preview=reader.get_data(300);reader.close()
        previewpath=out/(geometry+'-preview.png');imageio.imwrite(previewpath,preview)
        comparisons.append(dict(geometry=geometry,path=str(target.relative_to(R)),sha256=sha(target),preview=str(previewpath.relative_to(R)),preview_sha256=sha(previewpath),duration_seconds=40,terminated_panels='Only final frame held after actual clip end, explicitly red-labelled; no simulated continuation'))
    manifest=dict(entries=rows,comparisons=comparisons,plan_sha256=sha(D/'VIDEO_PLAN.json'),backend='RTX4090 separate camera resimulations with batch1; H200 main inference uses full registered cohorts',selection=plan['selection'],warning='These are12 single-state demonstrations, correlated acrossmodels and not H200 success-rate estimates. Main C_endpoint W120 demonstration terminates at23.7s; all failures preserved.')
    (D/'VIDEO_DELIVERY.json').write_text(json.dumps(manifest,indent=2)+'\n')
    record('all_twelve_actual_videos_and_factual_comparisons_complete',evidence='research/width-student-distillation-20261002/VIDEO_DELIVERY.json',next='Inspect previews, publish originals and annotations; do not infer device causality from single-state discrepancies')

if __name__=='__main__':main()
