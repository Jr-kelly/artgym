"""Compose complete recorded episodes; annotations never control physics."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage(t):
    if t < 2: return '桌面初态与实际保持'
    if t < 5: return '脚本接近'
    if t < 8: return '脚本闭合'
    if t < 12: return '连续抬刀'
    if t < 16: return '持稳与实际历史采集'
    phase=int((t-16)//5)+1
    return f'第{(phase+1)//2}轮：'+('伸出并保持' if phase%2 else '缩回并保持')


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--output',type=Path,required=True);p.add_argument('--font',type=Path,default=Path('/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc'));a=p.parse_args()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    sources=[('g2-learned-heavy-pulse-v38','工程带阻力成功',(.2,.2)),('g2-learned-capacity-pulse-v39','较大工程阻力失败',(.5,.5))]
    font=ImageFont.truetype(str(a.font),25);small=ImageFont.truetype(str(a.font),20)
    writer=imageio.get_writer(a.output,fps=30,codec='libx264',quality=8,macro_block_size=16,ffmpeg_params=['-threads','2'])
    chapters=[];total=0
    try:
        for name,label,amplitudes in sources:
            folder=a.root/'runs/robust-knife-family-20261003/demo'/name
            report=json.loads((folder/'report.json').read_text());trace=np.load(folder/'trace.npz');frames=len(trace['time']);assert frames==1080
            parameters=json.loads((a.root/report['physical_asset']).with_name('parameters.json').read_text());lower=float(parameters['joint_lower'])
            whole=imageio.get_reader(folder/'continuous.mp4');close=imageio.get_reader(folder/'hand-closeup.mp4')
            begin=total
            try:
                for i,(first,second) in enumerate(zip(whole,close)):
                    assert i<frames
                    t=float(trace['time'][i]);canvas=Image.new('RGB',(1280,640),(18,22,28));draw=ImageDraw.Draw(canvas)
                    draw.text((14,8),f'G2 + Wuji v1 | {label} | 实际回合 {t:05.2f}s',font=font,fill='white')
                    draw.text((14,45),stage(t)+' | 脚本取刀 + 几何参考 + P50学习残差',font=small,fill=(205,215,230))
                    canvas.paste(Image.fromarray(first).resize((640,480)),(0,80));canvas.paste(Image.fromarray(second).resize((640,480)),(640,80))
                    contact=bool(trace['finger_slider_contacts'][i,0]>0)
                    draw.text((14,568),f'已记录评估：滑块位移 {(float(trace["slider"][i])-lower)*1000:5.1f} mm | 拇指—滑块接触 '+('有' if contact else '无'),font=small,fill=(185,230,185) if contact else (250,165,145))
                    draw.text((14,602),f'运行/起动幅值 {amplitudes[0]:.1f}/{amplitudes[1]:.1f} N；不是实物总阻力上限。连续物理回合，无阶段重置。',font=small,fill=(205,215,230))
                    writer.append_data(np.asarray(canvas));total+=1
                assert i+1==frames
            finally: whole.close();close.close()
            chapters.append(dict(source=str(folder.relative_to(a.root)),label=label,begin_frame=begin,frames=frames,source_full_success=report['full_success'],sources={x:sha(folder/x) for x in ['continuous.mp4','hand-closeup.mp4','trace.npz','report.json']}))
            print(json.dumps(dict(chapter=name,frames=frames)),flush=True)
    finally:writer.close()
    manifest=dict(output=a.output.name,sha256=sha(a.output),fps=30,frames=total,duration_seconds=total/30,chapters=chapters,scope='Full actual recorded episodes composed with synchronized whole/close views. Clock captions use fixed schedule; numerical/contact captions use saved evaluation-only traces. No re-simulation or actor-input change. No human attachment media.')
    a.output.with_suffix('.manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print(json.dumps(manifest,ensure_ascii=False))


if __name__=='__main__':main()
