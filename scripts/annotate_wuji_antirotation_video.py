"""Uncut dual-view video with evaluation-only force and relative-pose captions."""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
import imageio,numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.spatial.transform import Rotation
R=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--trial',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--title',required=True);a=p.parse_args();assert not a.output.exists();a.output.parent.mkdir(parents=True,exist_ok=True)
    t=np.load(a.trial/'trace.npz');report=json.loads((a.trial/'report.json').read_text());asset=R/report['physical_asset'];lower=float(ET.parse(asset).find('.//joint[@type="prismatic"]/limit').get('lower'))
    obj=Rotation.from_quat(t['object'][:,3:7]);wrist=Rotation.from_quat(t['wrist'][:,3:7]);rel=wrist.inv()*obj;origin=int(np.argmin(abs(t['time']-16)));angle=(rel[origin].inv()*rel).magnitude();active=(wrist[origin].inv()*wrist).magnitude()
    pressure=t['pair_slider_pressure_mean_N'][:,0];index=np.linalg.norm(t['pair_force_normal_contribution_world_mean_N'][:,1,0,:],axis=-1);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
    readers=[imageio.get_reader(str(a.trial/name)) for name in ['continuous.mp4','hand-closeup.mp4']];writer=imageio.get_writer(str(a.output),fps=30,codec='libx264',quality=7,ffmpeg_params=['-threads','2']);count=0;keyframes={180:'pickup',630:'extension',1074:'return'}
    try:
        for i,(wide,close) in enumerate(zip(*readers)):
            assert i<len(t['time']);clock=float(t['time'][i]);phase='SETTLE' if clock<2 else 'APPROACH' if clock<5 else 'CLOSE' if clock<8 else 'LIFT' if clock<12 else 'SUPPORT TRANSFER / HOLD' if clock<16 else ('EXTEND / HOLD' if int((clock-16-1e-7)//5)%2==0 else 'RETRACT / HOLD')
            canvas=Image.new('RGB',(1280,608),(15,21,31));canvas.paste(Image.fromarray(wide).resize((640,480)),(0,128));canvas.paste(Image.fromarray(close).resize((640,480)),(640,128));d=ImageDraw.Draw(canvas)
            lines=[a.title+' | G2 + Wuji v1 | continuous simulation',f't={clock:5.2f}s | {phase} | rail travel={(float(t["slider"][i])-lower)*1000:5.1f} mm | command=40 mm during extension',f'Pair NORMAL only: thumb-slider={pressure[i]:.3f} N | index-handle resultant={index[i]:.3f} N | frictional traction unavailable',f'Knife / wrist rotation since16s={angle[i]:.3f} rad | active wrist rotation={active[i]:.3f} rad'+(' | pre16 reference shown only for context' if clock<16 else ''),'Evaluation truth is captions only; actor gets measured joints, issued history, once initial estimate. No real robot.']
            for line,y in zip(lines,[5,29,53,77,102]):d.text((12,y),line,font=small if y>=53 else font,fill='white')
            writer.append_data(np.asarray(canvas));count+=1
            if i in keyframes:canvas.save(a.output.parent/(a.output.stem+'-'+keyframes[i]+'.png'))
    finally:
        writer.close()
        for reader in readers:reader.close()
    assert count==len(t['time'])==1080
    receipt=dict(title=a.title,trial=str(a.trial),frames=count,fps=30,duration_seconds=count/30,trace_sha256=hashlib.sha256((a.trial/'trace.npz').read_bytes()).hexdigest(),video_sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),scope='Uncut original physicalepisode, synchronized wide/hand views. Postprocessed truth captions only; normal contribution excludes friction. Not actorforcefeedback, stitched episodes, actualrealworld force or realrobot result.')
    a.output.with_suffix('.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
if __name__=='__main__':main()
