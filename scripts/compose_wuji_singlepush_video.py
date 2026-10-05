"""Synchronize both uncut simulator cameras and recorded offline diagnostics.
Never a robot video or controller input. No private reference photographs used.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import imageio.v2 as imageio
from PIL import Image,ImageDraw,ImageFont

def main():
 p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();a.output.parent.mkdir(parents=True,exist_ok=True)
 t=np.load(a.trial/'trace.npz');ev=json.loads((a.trial/'extension-evaluation.json').read_text());report=json.loads((a.trial/'report.json').read_text());q=(t['slider']-ev['prepush_slider_m'])*1000;seconds=t['time'];n=len(seconds)
 fonts='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';large=ImageFont.truetype(fonts,27);small=ImageFont.truetype(fonts,21)
 readers=[imageio.get_reader(a.trial/name) for name in ['continuous.mp4','hand-closeup.mp4']]
 assert all(abs(r.get_meta_data()['fps']-30)<1e-6 and abs(r.get_meta_data()['duration']-n/30)<.04 for r in readers)
 base=Image.new('RGB',(1920,1080),(19,25,35));d=ImageDraw.Draw(base);status='PASS: ALL DECLARED CHECKS' if ev['pass_all'] else 'DEVELOPMENT: TASK CHECKS FAILED'
 d.text((26,12),'G2 + WUJI | NEW KNIFE | SINGLE PUSH + HOLD | SIMULATION',font=large,fill='white');d.text((1060,12),status,font=large,fill=(114,228,150) if ev['pass_all'] else (255,181,90));d.text((26,48),'Full scene',font=small,fill=(190,200,215));d.text((986,48),'Hand camera | same timestamps | no cuts',font=small,fill=(190,200,215))
 x0,y0,x1,y1=480,837,1880,1027
 def px(v):return x0+(x1-x0)*v/22
 def py(v):return y1-(y1-y0)*(v+10)/65
 d.rectangle((x0,py(50),x1,py(20)),fill=(30,68,49));d.line((px(16),y0,px(16),y1),fill=(255,181,90),width=2)
 for value in [-10,0,15,35,55]:
  d.line((x0,py(value),x1,py(value)),fill=(65,75,88));d.text((422,py(value)-10),str(value),font=small,fill=(190,200,215))
 d.line([(px(float(s)),py(float(v))) for s,v in zip(seconds,q)],fill=(90,214,243),width=3)
 for value in [0,4,8,12,16,20,22]:
  d.line((px(value),y0,px(value),y1),fill=(58,68,83));d.text((px(value)-12,1031),str(value),font=small,fill=(190,200,215))
 d.text((710,1054),'Active slider displacement from pre-push (mm) | time (s) | green: >20 mm',font=small,fill=(190,200,215))
 writer=imageio.get_writer(a.output,fps=30,codec='libx264',quality=8,macro_block_size=1,ffmpeg_params=['-threads','4','-pix_fmt','yuv420p'])
 try:
  for i in range(n):
   im=base.copy();im.paste(Image.fromarray(readers[0].get_data(i)),(0,80));im.paste(Image.fromarray(readers[1].get_data(i)),(960,80));draw=ImageDraw.Draw(im);s=float(seconds[i]);phase='pickup / regrasp' if s<16 else ('single push' if s<20.04 else 'hold')
   draw.text((26,816),'t = %.2f s | %s'%(s,phase),font=large,fill='white');draw.text((26,858),'Actual slider: %+.2f mm'%q[i],font=large,fill=(90,214,243));draw.text((26,900),'Command: %.0f mm, then hold'%(report['task_stroke_m']*1000),font=small,fill='white')
   capacity=float(t['solver_brake_capacity_N'][i]);draw.text((26,934),'Brake capacity (model): %.3f N'%capacity,font=small,fill='white');draw.text((26,966),'75 gf reference = 0.7355 N',font=small,fill=(190,200,215));draw.text((26,1005),'No robot / no measured force curve',font=small,fill=(255,181,90));draw.line((px(s),y0,px(s),y1),fill='white',width=2);draw.ellipse((px(s)-6,py(float(q[i]))-6,px(s)+6,py(float(q[i]))+6),fill='white');writer.append_data(np.asarray(im))
   if i==min(n-1,600):im.save(a.output.with_suffix('.jpg'))
 finally:
  writer.close()
  for r in readers:r.close()
 metadata=dict(scope=__doc__,uncut=True,frames=n,fps=30,duration_s=n/30,task_pass=ev['pass_all'],source_trial=str(a.trial),sources={name:hashlib.sha256((a.trial/name).read_bytes()).hexdigest() for name in ['continuous.mp4','hand-closeup.mp4','trace.npz','extension-evaluation.json']},video_sha256=hashlib.sha256(a.output.read_bytes()).hexdigest());a.output.with_suffix('.json').write_text(json.dumps(metadata,indent=2));print(json.dumps(metadata))
if __name__=='__main__':main()
