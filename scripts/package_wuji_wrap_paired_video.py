"""Two independent uncut held diagnostics; never a continuous pickup claim."""
import argparse, hashlib, json
from pathlib import Path
import imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    assert not a.output.exists(); a.output.parent.mkdir(parents=True,exist_ok=True)
    base=Path('runs/wrap-force-20261004/comparison')
    cases=[('Original source2',base/'source2-original-pressure080-v3'),
           ('Index under-wrap',base/'index-wrap-v8-pressure080-v3')]
    traces=[np.load(path/'trace.npz') for _,path in cases]
    assert np.allclose(traces[0]['time'],traces[1]['time'])
    evaluations=[json.loads((path/'functional-evaluation.json').read_text()) for _,path in cases]
    reports=[json.loads((path/'report.json').read_text()) for _,path in cases]
    assert all(r['held_diagnostic'] for r in reports)
    key='runs/wrap-force-20261004/train/paired-held-single1-pilot-v1r1/update_000120.pth'
    assert reports[0]['weight_sha256'][key]==reports[1]['weight_sha256'][key]
    readers=[imageio.get_reader(str(path/'hand-closeup.mp4')) for _,path in cases]
    writer=imageio.get_writer(str(a.output),fps=30,codec='libx264',quality=7,ffmpeg_params=['-threads','2'])
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
    count=0
    try:
        for i,frames in enumerate(zip(*readers)):
            canvas=Image.new('RGB',(1280,640),(15,21,31)); draw=ImageDraw.Draw(canvas)
            draw.text((12,5),'PAIRED HELD DIAGNOSTICS | two independent original-knife recordings | not pickup demos',font=font,fill='white')
            draw.text((12,30),'Same S120, 0.8 model-pressure tier, matched per-grip priors and full40mm references; original physical limits.',font=small,fill='white')
            draw.text((12,53),'A is actual pair NORMAL; original B axial traction and actual C rail reaction remain unavailable.',font=small,fill='white')
            draw.text((12,75),'Base brake capacity=0.2 N is a parameter, not force. Truth captions are evaluation only.',font=small,fill='white')
            for column,((label,_),frame,z,ev) in enumerate(zip(cases,frames,traces,evaluations)):
                x=column*640; clock=float(z['time'][i]); position=(float(z['slider'][i])+.03267458688196273)*1000
                draw.text((x+12,101),label+' | full functional diagnostic '+('PASS' if ev['functional_behavior_pass'] else 'FAIL'),font=font,fill='white')
                draw.text((x+12,125),'t=%.2fs | position=%.1fmm | actual A=%.3fN'%(clock,position,float(z['pair_slider_pressure_mean_N'][i,0])),font=small,fill='white')
                canvas.paste(Image.fromarray(frame).resize((640,480)),(x,160))
            writer.append_data(np.asarray(canvas)); count+=1
            if i in [480,780,1074]:canvas.save(a.output.parent/(a.output.stem+'-frame%d.png'%i))
    finally:
        writer.close()
        for reader in readers: reader.close()
    assert count==1080==len(traces[0]['time'])
    receipt=dict(scope=__doc__,frames=count,duration_seconds=count/30,fps=30,
        video_sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),
        actor_sha256=reports[0]['weight_sha256'][key],
        sources=[dict(label=label,trial=str(path),
            source_video_sha256=hashlib.sha256((path/'hand-closeup.mp4').read_bytes()).hexdigest(),
            trace_sha256=hashlib.sha256((path/'trace.npz').read_bytes()).hexdigest(),
            evaluation=ev) for (label,path),ev in zip(cases,evaluations)])
    a.output.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(a.output)


if __name__=='__main__': main()
