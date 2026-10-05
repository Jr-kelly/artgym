"""Uncut full/close synchronized recordings; trace values are evaluation only."""
import hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
import imageio,numpy as np
from PIL import Image,ImageDraw,ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1];B=R/'runs/highload-20261005';OUT=B/'media'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def video(name,path,label,seconds):
 target=OUT/name
 if target.exists():return
 readers=[imageio.get_reader(str(path/f)) for f in ['continuous.mp4','hand-closeup.mp4']];z=np.load(path/'trace.npz');ev=json.loads((path/'functional-evaluation.json').read_text());lower=float(ET.parse(R/'assets/objects/knife_wuji_real_size_20261002/000/mobility.urdf').find('.//joint/limit').get('lower'))
 font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
 writer=imageio.get_writer(str(target),fps=30,codec='libx264',quality=7,ffmpeg_params=['-threads','2']);count=0
 try:
  for i,frames in enumerate(zip(*readers)):
   canvas=Image.new('RGB',(1280,608),(15,21,31));d=ImageDraw.Draw(canvas)
   d.text((12,8),label,font=font,fill='white');d.text((12,35),'G2 + Wuji | 40 mm command | simulation only | evaluation captions, not controller inputs',font=font,fill='white')
   d.text((12,64),'t=%.2fs | slider from lower=%.2f mm | normal A=%.3f N | original criterion: %s'%(z['time'][i],(z['slider'][i]-lower)*1000,z['pair_slider_pressure_mean_N'][i,0],'PASS' if ev['continuous_pickup_demo_pass'] else 'FAIL'),font=font,fill='white')
   d.text((12,92),'Full continuous episode; no cuts or state resets. Original axial B / rail C remain unmeasured.',font=font,fill='white')
   for col,frame in enumerate(frames):canvas.paste(Image.fromarray(frame).resize((640,480)),(col*640,128))
   writer.append_data(np.asarray(canvas));count+=1
   if i in [240,542,844,1144,count-1] and i in [240,542,844,1144]:canvas.save(OUT/(target.stem+'-frame%d.jpg'%i))
 finally:
  writer.close()
  for r in readers:r.close()
 assert count==seconds*30,(count,seconds)
 target.with_suffix('.json').write_text(json.dumps(dict(frames=count,fps=30,duration_s=seconds,sha256=digest(target),trial=str(path.relative_to(R)),source_sha256={f:digest(path/f) for f in ['continuous.mp4','hand-closeup.mp4','trace.npz']}),indent=2))
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 video('highload050-three-cycles.mp4',B/'continuous/tracking1-threecycle-video-v1','Tracking1 .50 | first two endpoint-capable; third-cycle deterioration',46)
 video('capacity020-plus005.mp4',B/'capacity/tracking1-load020-added0.05-video-v3','Tracking1 .20 brake profile + .05 N balanced opposing test load | complete task PASS',36)
 fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
 paths=[('Tracking1 .50, three cycles',B/'continuous/tracking1-threecycle-video-v1'),('Tracking1 .20 + .05 N test',B/'capacity/tracking1-load020-added0.05-video-v3')]
 for label,path in paths:
  z=np.load(path/'trace.npz');relative=np.load(path/'relative-hand-evaluation.npz');mask=z['time']>=16;t=z['time'][mask]
  for ax,v in zip(axes,[(z['slider']-float(ET.parse(R/'assets/objects/knife_wuji_real_size_20261002/000/mobility.urdf').find('.//joint/limit').get('lower')))*1000,np.linalg.norm(relative['relative_rotvec_rad'],axis=1),z['pair_slider_contact_substep_fraction'][:,0]]):ax.plot(t,v[mask],label=label)
 for ax,label in zip(axes,['Slider position from lower (mm)','Relative rotation (rad)','Thumb contact fraction']):
  ax.set_ylabel(label);ax.grid(alpha=.2)
  for t in [21,26,31,36,41]:ax.axvline(t,color='black',alpha=.15)
 axes[0].axhline(25,color='green',ls=':');axes[0].axhline(8,color='red',ls=':');axes[1].axhline(.6,color='red',ls=':');axes[0].legend();axes[-1].set_xlabel('Continuous episode time (s)');fig.tight_layout()
 for suffix in ['png','pdf']:fig.savefig(OUT/('highload-behavior.'+suffix),dpi=160)
if __name__=='__main__':main()
