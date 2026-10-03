"""Unspliced synchronized panorama/closeup with evaluation-only pressure labels."""
import argparse,pathlib,json
import imageio.v2 as imageio
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.spatial.transform import Rotation
p=argparse.ArgumentParser();p.add_argument('--episode',type=pathlib.Path,required=True);a=p.parse_args();z=np.load(a.episode/'trace.npz');r=json.loads((a.episode/'report.json').read_text());overview=imageio.get_reader(a.episode/'continuous.mp4');close=imageio.get_reader(a.episode/'hand-closeup.mp4');font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',19);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16);writer=imageio.get_writer(a.episode/'pressure-annotated.mp4',fps=30,codec='libx264',quality=7,macro_block_size=1);keys=[];reference=z['object'][np.argmin(abs(z['time']-16))];reference_r=Rotation.from_quat(reference[3:7]);phases=['settle/approach','close','lift','hold + real history','operate']
frame_count=0
for i,(pan,hand) in enumerate(zip(overview,close)):
 if i>=len(z['time']):break
 # Two cameras from one uninterrupted episode, synchronized frame for frame.
 frame=Image.new('RGB',(1920,832),(14,18,24));frame.paste(Image.fromarray(pan),(0,0));frame.paste(Image.fromarray(hand),(960,0));draw=ImageDraw.Draw(frame);t=float(z['time'][i]);normal=z['pair_slider_pressure_mean_N'][i,0];contact=z['finger_slider_contacts'][i,0]>0;ring=z['pair_underside_support_mean_N'][i,3];obj=z['object'][i];drift=np.linalg.norm(obj[:3]-reference[:3])*1000;angle=(reference_r.inv()*Rotation.from_quat(obj[3:7])).magnitude();command_t=t-1/30;goal=40 if command_t>=16-1e-7 and int((command_t-16+1e-7)/5)%2==0 else 0;travel=(z['slider'][i]-z['slider'][0])*1000;cap=z['solver_brake_capacity_N'][i];label=phases[int(z['phase'][i])];label='learned hold preparation' if r.get('learned_takeover_seconds') is not None and r['learned_takeover_seconds']<16 and r['learned_takeover_seconds']<=command_t<16 else label;estimate=z['estimated_thumb_pressure_N'][i]
 lines=[f't={t:5.2f}s | {label} | external goal={goal}mm | actual rail travel={travel:5.1f}mm',f'Thumb -> slider: contact={contact} | measured normal={normal:.3f}N (native pairs,240Hz,8-step mean) | ring underside={ring:.3f}N',f'Body drift={drift:.2f}mm / angle={angle:.3f}rad (relative to handover; thresholds10mm/.25rad) | passive brake CAPACITY={cap:.3f}N',(f'Joint-model pressure estimate={estimate:.3f}N; not a force sensor' if np.isfinite(estimate) else 'Joint-model pressure adjustment: disabled; motor targets may vary')+' | object/contact state used for display only']
 for j,line in enumerate(lines):draw.text((18,726+j*25),line,font=font if j<2 else small,fill=(232,242,248))
 writer.append_data(np.asarray(frame));frame_count+=1
 if i in [0,239,479,599,719,839,959,1079]:
  key=frame.resize((960,416));keys.append(key);key.save(a.episode/f'key-{i:04d}.jpg',quality=92)
writer.close();overview.close();close.close();sheet=Image.new('RGB',(1920,416*4),(255,255,255))
for i,key in enumerate(keys):sheet.paste(key,((i%2)*960,(i//2)*416))
sheet.save(a.episode/'keyframes.jpg',quality=93);(a.episode/'annotation.json').write_text(json.dumps(dict(source=['continuous.mp4','hand-closeup.mp4'],frames=frame_count,fps=30,scope='Synchronizedsingleepisode; no phase stitching,truth usedonlydiagnostics. Meanpairnormal force ismeasurement; brakecapacity isparameter; motorlagpressure ismodelestimate.',full_success=r['full_success']),indent=2))
