"""Annotate native asset views and create a gravity/mounting figure plus local video report."""
import json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'research/rear-sim2real-20261009';M=D/'media'
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',25);small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',19)
r=json.loads((M/'placement-render.json').read_text());obj=np.array(r['object_world']);wrist=np.array(r['wrist_world']);gravity=wrist[:3,:3].T@np.array([0.,0.,-1.]);q=r['slider_q_m']
def point(local):return (obj@np.r_[local,1])[:3]
def project(p,cam):
    eye=np.array(cam['eye']);aim=np.array(cam['aim']);f=aim-eye;f/=np.linalg.norm(f);right=np.cross(f,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,f);v=p-eye;z=v@f;t=math.tan(math.radians(cam['horizontal_fov']/2));return np.array([600+600*(v@right)/(z*t),450-600*(v@up)/(z*t)])
def arrow(d,label,xy,at,color='#ffe17a'):
    xy=np.array(xy,float);at=np.array(at,float);d.rounded_rectangle([*xy,xy[0]+len(label)*26+12,xy[1]+37],radius=6,fill='#172330');d.text(xy+np.array([6,0]),label,font=font,fill=color);start=xy+np.array([len(label)*13,37]);d.line([tuple(start),tuple(at)],fill=color,width=4);v=(start-at);v/=max(np.linalg.norm(v),1);normal=np.array([-v[1],v[0]]);d.polygon([tuple(at),tuple(at+v*16+normal*7),tuple(at+v*16-normal*7)],fill=color)
for cam in r['camera']:
    label=cam['view'];im=Image.open(M/(label+'.png'));d=ImageDraw.Draw(im)
    tail=project(point([0,0,-.072]),cam);cap=project(point([0,.006,-.026+q]),cam);tip=project(point([0,0,.072]),cam)
    print(label,'tail',tail,'cap',cap,'tip',tip)
    d.rectangle([0,0,1200,42],fill='#172330');d.text((18,5),{'front':'摆刀正面：滑块面朝拇指','side':'摆刀侧面：非拇指承托刀身','thumb-slider':'拇指与滑块近景：指腹压在滑块上'}[label],font=font,fill='white')
    if label!='thumb-slider':
        arrow(d,'刀尾', [990,720],tail);arrow(d,'刀尖方向', [30,730],tip)
        arrow(d,'滑块 / 拇指指腹', [760,60],cap)
    else:arrow(d,'滑块凸起 2 mm', [750,55],cap)
    if label=='side':
        contacts=[json.loads(l) for l in (ROOT/'runs/rear-sim2real-20261009/final/nominal-video-v6/contacts.jsonl').read_text().splitlines()]
        stamp=min([c['time_s'] for c in contacts],key=lambda v:abs(v-r['time_s']))
        for digit,title,where in [('index','食指承托区',[60,630]),('middle','中指承托区',[430,700]),('pinky','小指刀尾承托区',[800,650])]:
            cs=[c for c in contacts if c['time_s']==stamp and c['body0']=='link_0' and '_'+digit+'_' in c['body1']]
            if cs:
                c=max(cs,key=lambda c:c['normal_solver_N']);at=project(point(c['local_point0_m']),cam);arrow(d,title,where,at,color='#80efb7')
    d.rectangle([0,850,1200,900],fill='#172330');d.text((18,854),'原生资产按实际持刀姿态渲染；不是实物照片。摆放后须撤去外部承托。',font=small,fill='white');im.save(M/(label+'-annotated.png'))
# Mounting figure includes the whole arm and an explicit wrist gravity vector.
import imageio.v2 as imageio
reader=imageio.get_reader(str(ROOT/'runs/rear-sim2real-20261009/final/nominal-video-v6/overall.mp4'));wide=Image.fromarray(reader.get_data(190)).resize((960,720));reader.close();im=Image.new('RGB',(1450,800),'#101a26');im.paste(wide,(10,50));d=ImageDraw.Draw(im);d.text((25,7),'固定腕姿：复现此方向；G2 只保持，支架也须保持相同朝向',font=font,fill='white');arrow(d,'重力竖直向下',[800,160],[875,470],color='#79d8ff');d.text((990,130),'腕坐标中重力方向',font=font,fill='#79d8ff');d.text((990,190),'g / |g| =',font=font,fill='white');d.text((990,240),'[%.4f, %.4f, %.4f]'%tuple(gravity),font=small,fill='white');d.text((990,320),'腕原点与轴按 URDF',font=small,fill='white');d.text((990,370),'不能把掌心随意翻转',font=small,fill='white');d.text((990,420),'不需要动态机械臂控制',font=small,fill='white');d.text((25,760),'白色摆刀托板只在 0–3 s 出现；之后没有刀身夹具、外力托举或滑轨驱动。',font=small,fill='#d1d9e5');im.save(M/'mounting.png')
(D/'MOUNTING.json').write_text(json.dumps(dict(wrist_world=wrist.tolist(),unit_gravity_in_wrist=gravity.tolist(),scope='Known fixed orientation; verify actual G2/fixture mounting locally'),indent=2))
