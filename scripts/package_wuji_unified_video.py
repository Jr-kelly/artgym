"""Label four fixed-reset panels; visualization is separate from final statistics."""
import argparse,json,subprocess,hashlib
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--label',required=True);a=p.parse_args();r=json.loads((a.input/'report.json').read_text());assert r['initial_state_rows']==[0,32,64,96] and len(r['records'])==4
 assert not a.output.exists();a.output.parent.mkdir(parents=True,exist_ok=True);font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';cp=r['checkpoint_sha256'];sec=r['protocol']['stage_seconds'];label=a.label.replace(':',' ').replace("'",'')
 filters=['[0:v]split=4[v0][v1][v2][v3]','[v0]crop=512:384:0:0[p0]','[v1]crop=512:384:512:0[p1]','[v2]crop=512:384:1024:0[p2]','[v3]crop=512:384:0:384[p3]','[p0][p1][p2][p3]hstack=inputs=4,pad=2048:480:0:64:black[grid]']
 header=f'{label} | SAME WEIGHTS all 4 sources | privileged teacher | fixed {sec:g}s commands | SHA {cp[:12]}'
 draw=f"[grid]drawtext=fontfile={font}:text='{header}':x=14:y=9:fontsize=23:fontcolor=white,drawtext=fontfile={font}:text='Separate fixed development examples; video outcomes are not frozen batch statistics. Simulation only.':x=14:y=38:fontsize=18:fontcolor=white"
 for source,row in enumerate(r['records']):
  ok=row['stable_full_all_endpoints'];text=f'Source {source} | example STRICT '+('PASS' if ok else 'FAIL');color='lime' if ok else 'red';draw+=f",drawtext=fontfile={font}:text='{text}':x={source*512+15}:y=452:fontsize=22:fontcolor={color}"
 filters.append(draw+'[out]');subprocess.run(['ffmpeg','-v','error','-i',str(a.input/'policy.mp4'),'-filter_complex',';'.join(filters),'-map','[out]','-an','-c:v','libx264','-crf','20','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(a.output)],check=True)
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(a.output)],text=True));assert abs(float(probe['format']['duration'])-20)<.2
 out=dict(video=str(a.output),sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),checkpoint_sha256=cp,source_rows=[0,32,64,96],seconds=sec,strict_examples=[x['stable_full_all_endpoints'] for x in r['records']],all_sources_same_weights=True,policy='privileged teacher, no source routing',scope='Separate resimulation, fixed development examples; not final statistics',probe=probe)
 a.output.with_suffix('.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='probe'}))
if __name__=='__main__':main()
