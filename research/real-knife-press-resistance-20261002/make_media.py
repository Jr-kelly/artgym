import json,subprocess
import imageio_ffmpeg
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation
from scripts.record_wuji_press_goal import R,D,record
from scripts.wuji_width_contract import sha
base=R/'runs/real-knife-press-resistance-20261002';out=base/'media';out.mkdir(exist_ok=True);fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True);hand=Rotation.from_rotvec([0,-np.pi/2,0])*Rotation.from_rotvec([np.pi/2,0,0]);row=8
for name,label,color in [('dev-variable-p0','0 mm','#3976b7'),('dev-variable-p0.5','0.5 mm','#df7f20')]:
 t=dict(np.load(base/'eval'/name/'trace.npz'));time=np.arange(1,len(t['active'])+1)/30;active=t['active'][:,row];rot=hand*Rotation.from_quat(t['object_rot'][:,row]);normal=rot.apply(np.tile([0,1,0],(len(time),1)));force=np.maximum(0,(t['contact_force'][:,row,0]*normal).sum(-1))
 for ax,values in zip(axes,[t['slider'][:,row]*1000,t['drift'][:,row]*1000,force]):ax.plot(time,np.where(active,values,np.nan),label=label,color=color,linewidth=1)
axes[0].plot(time,t['goal'][:,row]*1000,'k--',label='External command');axes[1].axhline(10,color='red',linestyle='--',label='Body threshold')
for ax,ylabel in zip(axes,['Slider joint position (mm)','Body displacement (mm)','Thumb net normal force proxy (N)']):ax.set_ylabel(ylabel);ax.grid(alpha=.2);ax.legend(loc='best')
axes[-1].set_xlabel('Simulation time (s)');fig.suptitle('H200 recorded dev trajectory: first source3 state, variable resistance peak0.05N\nBoth press settings fail K20/S5; contact force is a net-body proxy')
fig.tight_layout();fig.savefig(out/'paired-trajectory.png',dpi=160);fig.savefig(out/'paired-trajectory.pdf');plt.close(fig)
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';videos=[base/'video'/s/'policy.mp4' for s in ['zero','low']];reports=[json.loads((p.parent/'report.json').read_text()) for p in videos];dur=[r['recorded_steps']/30 for r in reports];maximum=max(dur);texts=['135x16x12mm body | C3200 | source3 same initial state | variable resistance peak 0.05N','0 mm extra bias | K20 FAIL | S5 FAIL','0.5 mm extra bias | K20 FAIL | S5 FAIL','RTX4090 separate camera re-simulation; failures preserved; not H200 statistics or hardware']
for i,text in enumerate(texts):(out/('label'+str(i)+'.txt')).write_text(text)
f=[]
for i,d in enumerate(dur):
 s='[%d:v]tpad=stop_mode=clone:stop_duration=%.6f,trim=duration=%.6f'%(i,maximum-d,maximum)
 if d<maximum:s+=",drawtext=fontfile="+font+":text='ENDED - last frame':enable='gte(t,%.6f)':x=10:y=50:fontsize=24:fontcolor=red:box=1:boxcolor=black"%d
 f.append(s+'[v%d]'%i)
f.append('[v0][v1]hstack=inputs=2,pad=1024:500:0:80:black[grid]');draw='[grid]'
for i,x,y,size in [(0,8,8,19),(1,8,53,18),(2,520,53,18),(3,8,475,15)]:draw+='drawtext=fontfile='+font+':textfile='+str(out/('label'+str(i)+'.txt'))+':x='+str(x)+':y='+str(y)+':fontsize='+str(size)+':fontcolor='+('red' if i in [1,2] else 'white')+','
f.append(draw.rstrip(',')+'[out]');video=out/'press-variable-paired.mp4';subprocess.run([ffmpeg,'-v','error','-i',str(videos[0]),'-i',str(videos[1]),'-filter_complex',';'.join(f),'-map','[out]','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
subprocess.run([ffmpeg,'-v','error','-ss','0.5','-i',str(video),'-frames:v','1',str(out/'press-preview.png')],check=True)
j=dict(video=str(video.relative_to(R)),sha256=sha(video),raw_durations_s=dur,paired_duration_s=maximum,source=3,dev_row=8,video_local_row=0,source_mapping='The one-row camera files use local row0; original source is3 as registered inVIDEO.json',scope='SeparateRTXsingle-statecameraresimulation; 20s requested, all actual available frames retained, shorter endedclip explicitlymarked. Not counted inH200statistics')
(D/'VIDEO_RESULT.json').write_text(json.dumps(j,indent=2)+'\n');record('one_paired_video_and_targeted_failure_curve_created',evidence='research/real-knife-press-resistance-20261002/VIDEO_RESULT.json',next='Inspect preview thenpublishonecompact evidencepacket andvideo')
