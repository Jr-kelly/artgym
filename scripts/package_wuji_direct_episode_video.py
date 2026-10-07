"""Join the two native cameras of one episode, preserving all frames and speed."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import imageio,imageio_ffmpeg,numpy as np
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--caption',default='DEVELOPMENT - Goal not passed - same physical episode');a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    names=['continuous.mp4','hand-closeup.mp4'];counts=[];fps=[]
    for n in names:
        r=imageio.get_reader(str(a.trial/n));counts.append(r.count_frames());fps.append(r.get_meta_data()['fps']);r.close()
    with np.load(a.trial/'trace.npz') as z:frames=len(z['time'])
    assert counts==[frames,frames] and fps==[30.,30.],(counts,frames,fps)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    # Caption is constrained to plain text to keep ffmpeg's filter grammar
    # separate from arbitrary file/user text.
    assert all(c.isalnum() or c in ' -.,' for c in a.caption)
    filt="[0:v]scale=640:480[L];[1:v]scale=640:480[R];[L][R]hstack=inputs=2,pad=1280:520:0:40:black,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='"+a.caption+"':x=12:y=10:fontsize=18:fontcolor=white[V]"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-i',str(a.trial/names[0]),'-i',str(a.trial/names[1]),'-filter_complex',filt,'-map','[V]','-an','-c:v','libx264','-preset','fast','-crf','20','-threads','2',str(a.output)],check=True)
    r=imageio.get_reader(str(a.output));assert r.count_frames()==frames;r.close()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    receipt=dict(trial=str(a.trial),frames=frames,fps=30,duration_s=frames/30.,caption=a.caption,
                 trace_sha256=sha(a.trial/'trace.npz'),source_video_sha256={n:sha(a.trial/n)for n in names},
                 output_sha256=sha(a.output),recorded_initializer=(a.trial/'recorded-initialization.json').exists(),
                 scope='Same episode native wide/near frame indices, all frames uncut at original30fps; no stitched episodes, speedup, physics change or real robot claim')
    a.output.with_suffix('.json').write_text(json.dumps(receipt,indent=2));e=record('same_episode_synchronized_video_packaged',[str(a.output),str(a.output.with_suffix('.json'))],config=receipt,next_step='Inspect whole time axis and actual states/contact; video does not convert failed development trial to acceptance')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+str(a.output)+' all'+str(frames)+' nativepairedframes/original30fps; statuscaption '+a.caption+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
