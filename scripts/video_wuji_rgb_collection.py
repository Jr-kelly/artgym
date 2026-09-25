"""Encode saved camera frames without text, replay, interpolation, or policy changes."""
import argparse
import hashlib
import json
from pathlib import Path
import imageio.v2 as imageio
import numpy as np


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--rows',type=int,nargs='+')
    args=p.parse_args();assert not args.output.exists()
    status=json.loads((args.run/'collection-status.json').read_text());assert status['status']=='completed'
    selected=status['selected_initial_rows'];rows=args.rows or selected[:3]
    indexes=[selected.index(i) for i in rows];assert 1<=len(indexes)<=4
    fps=30 if status['frames']==599 else 10;assert status['frames'] in [200,599]
    frames=0;first=None;last=None;hashes={}
    writer=imageio.get_writer(args.output,fps=fps,codec='libx264',quality=8,macro_block_size=16)
    try:
        for c in status['chunks']:
            path=args.run/c['path'];sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==c['sha256']
            hashes[c['path']]=sha
            with np.load(path) as z:
                for step,images in zip(z['step'],z['rgb']):
                    assert last is None or int(step)-last==(1 if fps==30 else 3)
                    first=int(step) if first is None else first;last=int(step)
                    writer.append_data(np.concatenate(images[indexes],axis=1));frames+=1
    finally:writer.close()
    assert frames==status['frames']
    report=json.loads((args.run/'report.json').read_text())
    meta=dict(source=str(args.run),initial_state_rows=rows,fps=fps,frames=frames,first_control_step=first,last_control_step=last,
        text_overlay=False,synthetic_interpolation=False,physics_replayed=False,
        policy=status.get('physics_collection_policy','teacher'),artifact_sha256=status.get('actor_artifact_sha256'),
        clock_seconds=status['clock_seconds'],records={str(i):report['records'][selected.index(i)] for i in rows},
        video_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),source_chunks_sha256=hashes,
        scope='Actual saved simulator camera frames from the named run. These rows are old development data; video is illustrative, not independent validation.')
    args.output.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n');print(args.output)


if __name__=='__main__':main()
