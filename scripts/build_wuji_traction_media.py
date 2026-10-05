"""Uncut 36-second simulation comparisons and physical trace plots."""
import hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
import imageio,numpy as np
from PIL import Image,ImageDraw,ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1];B=R/'runs/traction-20261005';OUT=B/'media'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def video(name,cases,title):
    target=OUT/name;assert not target.exists()
    readers=[imageio.get_reader(str(path/filename)) for label,path,filename in cases]
    traces=[np.load(path/'trace.npz') for _,path,_ in cases]
    evaluations=[json.loads((path/'functional-evaluation.json').read_text()) for _,path,_ in cases]
    lower=float(ET.parse(R/'assets/objects/knife_wuji_real_size_20261002/000/mobility.urdf').find('.//joint/limit').get('lower'))
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
    writer=imageio.get_writer(str(target),fps=30,codec='libx264',quality=7,ffmpeg_params=['-threads','2'])
    count=0
    try:
        for i,frames in enumerate(zip(*readers)):
            canvas=Image.new('RGB',(1280,608),(15,21,31));draw=ImageDraw.Draw(canvas)
            draw.text((12,7),title,font=font,fill='white')
            draw.text((12,31),'Original G2 + Wuji physics | 40 mm command | truth captions for evaluation only | B/C unmeasured',font=font,fill='white')
            for col,((label,path,filename),frame,z,ev) in enumerate(zip(cases,frames,traces,evaluations)):
                x=col*640;draw.text((x+12,57),label+' | '+('PASS' if ev['continuous_pickup_demo_pass'] else 'FAIL'),font=font,fill='white')
                draw.text((x+12,82),'t=%.2fs | slider=%.2fmm | A normal=%.3fN'%(z['time'][i],(z['slider'][i]-lower)*1000,z['pair_slider_pressure_mean_N'][i,0]),font=font,fill='white')
                canvas.paste(Image.fromarray(frame).resize((640,480)),(x,128))
            writer.append_data(np.asarray(canvas));count+=1
            if i in [240,600,780,930,1074]:canvas.save(OUT/(target.stem+'-frame%d.jpg'%i))
    finally:
        writer.close()
        for reader in readers:reader.close()
    assert count==1080
    target.with_suffix('.json').write_text(json.dumps(dict(frames=count,fps=30,duration_s=36,sha256=digest(target),sources=[dict(label=label,trial=str(path.relative_to(R)),video=filename,sha256=digest(path/filename),trace_sha256=digest(path/'trace.npz')) for label,path,filename in cases]),indent=2))
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    old=R/'runs/wrap-force-20261004/validation/wrap-frozen-v12-load035-v1';new=B/'selected-full-video-v13/simulation';fail=B/'validation/selected-highload050-video-v16/simulation'
    video('traction035-continuous.mp4',[('V13 .35 full view',new,'continuous.mp4'),('V13 .35 close view',new,'hand-closeup.mp4')],'Complete continuous pickup and two cycles | base brake capacity .35 N, not measured resistance')
    video('baseline-v13-035-comparison.mp4',[('Baseline .35',old,'hand-closeup.mp4'),('V13 .35',new,'hand-closeup.mp4')],'Matched .35 profile | same grasp, S120 weights, original limits | different thumb controller')
    video('traction050-failure.mp4',[('V13 .50 full view',fail,'continuous.mp4'),('V13 .50 close view',fail,'hand-closeup.mp4')],'Representative failure | .50 capacity | no threshold change and no cuts')
    fig,axes=plt.subplots(4,1,figsize=(11,10),sharex=True)
    lower=float(ET.parse(R/'assets/objects/knife_wuji_real_size_20261002/000/mobility.urdf').find('.//joint/limit').get('lower'))
    for label,path,color in [('Baseline .35',old,'#bb5533'),('V13 .35',new,'#156caf'),('V13 .50',fail,'#777777')]:
        z=np.load(path/'trace.npz');rel=np.load(path/'relative-hand-evaluation.npz');t=z['time'];ids=t>=16
        values=[(z['slider']-lower)*1000,z['pair_slider_contact_substep_fraction'][:,0],z['pair_slider_pressure_mean_N'][:,0],np.linalg.norm(rel['relative_rotvec_rad'],axis=1)]
        for ax,v in zip(axes,values):ax.plot(t[ids],v[ids],label=label,color=color,linewidth=1.3)
    for ax,label in zip(axes,['Slider from lower (mm)','Thumb contact fraction','A normal (N)','Relative rotation (rad)']):
        ax.set_ylabel(label);ax.grid(alpha=.2)
        for t in [21,26,31]:ax.axvline(t,color='black',alpha=.2)
    axes[0].axhline(25,color='green',ls=':',alpha=.5);axes[0].axhline(8,color='red',ls=':',alpha=.5)
    axes[3].axhline(.6,color='red',ls=':',alpha=.5);axes[0].legend();axes[-1].set_xlabel('Continuous episode time (s)')
    fig.suptitle('Actual original-knife behavior | 40 mm command | axial B and rail C unavailable');fig.tight_layout()
    for suffix in ['png','pdf']:fig.savefig(OUT/('behavior-comparison.'+suffix),dpi=160)
    print(OUT)
if __name__=='__main__':main()
