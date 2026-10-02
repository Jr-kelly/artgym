import json,subprocess
import imageio_ffmpeg,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.record_wuji_real_size_goal import R,D,record
from scripts.wuji_width_contract import sha
B=R/'runs/real-size-student-adaptation-20261002';out=B/'media';out.mkdir(exist_ok=True);ffmpeg=imageio_ffmpeg.get_ffmpeg_exe();font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
for role,p,color in [('parent',B/'baseline/student','#777777'),('C800',B/'dev/real-C800','#2875b4'),('R800',B/'dev/real-R800','#d98219')]:
 t=dict(np.load(p/'trace.npz'));times=np.arange(1,len(t['active'])+1)/30;alive=t['active'][:,0]
 for ax,v in zip(axes,[t['slider'][:,0]*1000,t['drift'][:,0]*1000,t['rotation'][:,0]]):ax.plot(times,np.where(alive,v,np.nan),label=role,color=color)
axes[0].plot(times,t['goal'][:,0]*1000,'k--',label='External command');axes[1].axhline(10,color='red',linestyle='--');axes[2].axhline(.25,color='red',linestyle='--')
for ax,label in zip(axes,['Slider position (mm)','Body displacement (mm)','Body rotation (rad)']):ax.set_ylabel(label);ax.grid(alpha=.2);ax.legend()
axes[-1].set_xlabel('Simulation time (s)');fig.suptitle('H200 recorded dev: predeclared first source3 initial state\n135x16x12mm approximate body; zero added rail resistance');fig.tight_layout();fig.savefig(out/'paired-trajectory.png',dpi=160);fig.savefig(out/'paired-trajectory.pdf');plt.close(fig)
roles=['parent','C800','R800'];videos=[B/'video'/s/'policy.mp4' for s in roles];j=[json.loads((p.parent/'press-report.json').read_text()) for p in videos];dur=[json.loads((p.parent/'report.json').read_text())['recorded_steps']/30 for p in videos];maximum=max(dur);filters=[]
for i,d in enumerate(dur):
 text=roles[i]+' | K20 '+('PASS' if j[i]['K20'] else 'FAIL')+' | S5 '+('PASS' if j[i]['S5'] else 'FAIL');label=out/('label%d.txt'%i);label.write_text(text)
 s='[%d:v]tpad=stop_mode=clone:stop_duration=%.6f,trim=duration=%.6f'%(i,maximum-d,maximum)
 if d<maximum:s+=",drawtext=fontfile="+font+":text='ENDED - last frame':enable='gte(t,%.6f)':x=8:y=55:fontsize=24:fontcolor=red:box=1:boxcolor=black"%d
 s+=',pad=512:440:0:42:black,drawtext=fontfile='+font+':textfile='+str(label)+':x=8:y=12:fontsize=20:fontcolor=white[v%d]'%i;filters.append(s)
filters.append('[v0][v1][v2]hstack=inputs=3,pad=1536:490:0:35:black[grid]')
texts=['Approximate body135x16x12mm | same predeclared source3 dev state | zero added rail resistance','RTX4090 separate single-state camera simulations; failures preserved; not H200 statistics or hardware']
for i,s in enumerate(texts):(out/('header%d.txt'%i)).write_text(s)
filters.append('[grid]drawtext=fontfile='+font+':textfile='+str(out/'header0.txt')+':x=8:y=7:fontsize=20:fontcolor=white,drawtext=fontfile='+font+':textfile='+str(out/'header1.txt')+':x=8:y=473:fontsize=15:fontcolor=white[out]')
video=out/'real-size-student-paired.mp4';subprocess.run([ffmpeg,'-v','error',*[x for p in videos for x in ['-i',str(p)]],'-filter_complex',';'.join(filters),'-map','[out]','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
subprocess.run([ffmpeg,'-v','error','-ss','0.5','-i',str(video),'-frames:v','1',str(out/'preview.png')],check=True)
(D/'VIDEO_RESULT.json').write_text(json.dumps(dict(video=str(video.relative_to(R)),sha256=sha(video),raw_durations_s=dur,roles=roles,K20=[r['K20'] for r in j],S5=[r['S5'] for r in j],source=3,dev_row=0,scope='IndependentRTXsingle-state re-simulation; not counted as H200 independent evidence. Ended clips explicitly labeled.'),indent=2))
record('one_threeway_comparison_and_dev_curve_created',evidence='research/real-size-student-adaptation-20261002/VIDEO_RESULT.json',next='Inspect preview once then compact report and release')
