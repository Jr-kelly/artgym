"""Pair all frames of one development episode; never a full Goal acceptance."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import imageio.v2 as imageio
from PIL import Image,ImageDraw,ImageFont


def main():
    p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--label',required=True);a=p.parse_args()
    assert not a.output.exists();a.output.parent.mkdir(parents=True,exist_ok=True)
    z=np.load(a.trial/'trace.npz');times=z['time'];n=len(times);names=['continuous.mp4','hand-closeup.mp4']
    readers=[imageio.get_reader(a.trial/name) for name in names]
    for reader in readers:
        meta=reader.get_meta_data();assert abs(meta['fps']-30)<1e-6 and abs(meta['duration']-n/30)<.04
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',22)
    writer=imageio.get_writer(a.output,fps=30,codec='libx264',quality=8,macro_block_size=1,ffmpeg_params=['-threads','4','-pix_fmt','yuv420p'])
    try:
        for i,t in enumerate(times):
            wide=readers[0].get_data(i);near=readers[1].get_data(i);assert wide.shape==near.shape
            h,w=wide.shape[:2];im=Image.new('RGB',(2*w,h+64),(19,25,35));im.paste(Image.fromarray(wide),(0,64));im.paste(Image.fromarray(near),(w,64))
            d=ImageDraw.Draw(im);d.text((12,4),'SIM DEVELOPMENT | '+a.label+' | GOAL INCOMPLETE',font=font,fill='white')
            d.text((12,34),'same episode / frame %d / t=%.3fs / uncut / original 30fps'%(i,float(t)),font=font,fill=(205,215,225))
            writer.append_data(np.asarray(im))
    finally:
        writer.close()
        for r in readers:r.close()
    meta=dict(scope=__doc__,source_trial=str(a.trial),label=a.label,frames=n,fps=30,duration_s=n/30,
        same_episode=True,uncut=True,full_goal_accepted=False,
        sources={name:hashlib.sha256((a.trial/name).read_bytes()).hexdigest() for name in names+['trace.npz']},video_sha256=hashlib.sha256(a.output.read_bytes()).hexdigest())
    a.output.with_suffix('.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta))


if __name__=='__main__':main()
