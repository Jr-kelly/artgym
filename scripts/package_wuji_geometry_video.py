"""Pair separately rendered camera rollouts; label their own outcomes explicitly."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import imageio.v2 as imageio
import imageio_ffmpeg
def main():
 p=argparse.ArgumentParser();p.add_argument('--teacher',type=Path,required=True);p.add_argument('--student',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--sources',type=int,nargs='+',required=True);a=p.parse_args()
 reports=[json.loads((x/'report.json').read_text()) for x in [a.teacher,a.student]];receipts=[json.loads((x/'geometry-receipt.json').read_text()) for x in [a.teacher,a.student]]
 assert reports[0]['initial_states_sha256']==reports[1]['initial_states_sha256'];assert receipts[0]['protocol']==receipts[1]['protocol']
 n=len(a.sources);assert n<=3 and all(len(r['records'])==n for r in reports);width=512*n;assert not a.output.exists();a.output.parent.mkdir(parents=True,exist_ok=True)
 font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';g=receipts[0]['asset'];protocol=receipts[0]['protocol'];dims=g['dimensions_mm_LWT'];label=g['parameters']['label']
 filters=['[0:v][1:v]vstack=inputs=2,pad='+str(width)+':880:0:80:black[grid]']
 text=f'{label} L/W/T {dims[0]:g}/{dims[1]:g}/{dims[2]:g} mm | {protocol} | SAME INITIAL STATES'
 draw=f"[grid]drawtext=fontfile={font}:text='{text}':x=10:y=8:fontsize=20:fontcolor=white,drawtext=fontfile={font}:text='RTX4090 separate resimulation | simulation only | F uses true-slider arrival':x=10:y=37:fontsize=16:fontcolor=white"
 for model_idx,(r,rec) in enumerate(zip(reports,receipts)):
  for i,row in enumerate(r['records']):
   ok=row['functional'] if protocol=='F' else row['stable_full_all_endpoints'];body=row['body_stable'];caption=f"{rec['model']} s{a.sources[i]} | {'F' if protocol=='F' else 'STRICT'} {'PASS' if ok else 'FAIL'} | BODY {'PASS' if body else 'FAIL'}"
   draw+=f",drawtext=fontfile={font}:text='{caption}':x={512*i+8}:y={model_idx*384+82}:fontsize=19:fontcolor={'lime' if ok and body else 'red'}:box=1:boxcolor=black@0.7"
 draw+=",drawtext=fontfile="+font+":text='Video outcomes above are measured on these camera rollouts; H200 batch statistics are separate.':x=10:y=855:fontsize=15:fontcolor=white[out]";filters.append(draw)
 subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(a.teacher/'policy.mp4'),'-i',str(a.student/'policy.mp4'),'-filter_complex',';'.join(filters),'-map','[out]','-an','-c:v','libx264','-crf','20','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(a.output)],check=True)
 reader=imageio.get_reader(a.output);meta=reader.get_meta_data();count=reader.count_frames();imageio.imwrite(a.output.with_suffix('.png'),reader.get_data(min(150,count-1)));reader.close();expected=1200 if protocol=='F' else 600;assert count==expected
 result=dict(video=str(a.output),sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),frames=count,duration_s=meta['duration'],geometry=label,dimensions_mm_LWT=dims,protocol=protocol,sources=a.sources,cohort_sha256=reports[0]['initial_states_sha256'],rollouts=[str(a.teacher),str(a.student)],outcomes=[r['records'] for r in reports],scope='Separate RTX4090 camera resimulation; does not replace H200 statistics, no hardware; external commands, F true-slider scheduler')
 a.output.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='outcomes'}))
if __name__=='__main__':main()
