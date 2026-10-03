"""Standalone browsable Chinese report with embedded actual simulation media."""
import argparse,base64,html,json
from pathlib import Path

def data(path,mime):return 'data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--stage',default='阶段报告：工作进行中，尚未冻结候选');a=p.parse_args()
    root=Path(__file__).resolve().parents[1];base=root/'runs/support-pressure-20261003';episodes=['estimated-raised-heavy-delayed-film-v24','coordinated-passive-loaded-film-v14','nominal-noisier750-loaded-progress-film-v58','nominal-stroke-support-v36'];blocks=[]
    labels={'estimated-raised-heavy-delayed-film-v24':'滑块抬高 1 mm、带阻力、33 ms 执行延迟','coordinated-passive-loaded-film-v14':'协调四指承托的名义带阻力基线','nominal-noisier750-loaded-progress-film-v58':'联合训练的实质进展与剩余失败：持续压紧并推进，刀身仍越界','nominal-stroke-support-v36':'代表性失败：较大初始估计误差下的行程支撑分配候选'}
    for name in episodes:
        folder=base/'demo'/name;r=json.loads((folder/'report.json').read_text());pressure=r['pair_pressure'];ends=r['endpoints_mean_last03s_m'];label=labels[name]
        body=f'<section><h2>{html.escape(label)}</h2><video controls preload="metadata" poster="{data(folder/"key-0599.jpg","image/jpeg")}"><source src="{data(folder/"pressure-annotated.mp4","video/mp4")}" type="video/mp4"></video>'
        body+=f'<p>完整连续流程：{"通过" if r["full_success"] else "未通过"}。静止压紧 {pressure["static_thumb_pressure_mean_N"]:.3f} N，操作均值 {pressure["operation_thumb_pressure_mean_N"]:.3f} N、5%分位 {pressure["operation_thumb_pressure_5th_percentile_N"]:.3f} N；物理子步接触比例 {pressure["operation_thumb_contact_substep_fraction"]:.4f}。刀身最大转角 {r["operation_body_max_rotation_rad"]:.3f} rad。</p>'
        if not r['full_success']:
            onsets=r['failure_onsets_s'];height=onsets.get('height')
            body+=f'<p>本回合记为失败：刀身稳定判据首次越界约{onsets["body_stability"]:.2f}秒，'+(f'{height:.2f}秒跌落到高度阈值以下。跌落后的导轨读数不计作完成伸缩。' if height is not None else '刀身仍被持住，但转动超过原任务判据。')+'视频保留完整36秒，没有使用接触真值或力传感器控制。</p>'
            if name=='nominal-noisier750-loaded-progress-film-v58':
                body+='<p>这是新的同一联合权重：早期基线在该估计误差下约20–21 mm停止；联合策略现在保持正确滑块接触、食指承托并推过槽位，但完整demo仍未通过。不能把这一回合列为成功或独立泛化。</p>'
        body+=f'<p>两轮端点（伸出／缩回）：{ends[0]*1000:.1f}／{ends[1]*1000:.1f} mm，{ends[2]*1000:.1f}／{ends[3]*1000:.1f} mm。外部指令40 mm，原判据为伸出&gt;25 mm、缩回&lt;8 mm、刀身转角&lt;0.25 rad、平移&lt;10 mm；没有放宽。</p>'
        body+=f'<p><a href="../demo/{name}/continuous.mp4">原始全景 MP4</a> · <a href="../demo/{name}/hand-closeup.mp4">原始手部近景 MP4</a> · <a href="../demo/{name}/report.json">完整记录</a></p><details><summary>关键帧与力来源</summary><img src="{data(folder/"keyframes.jpg","image/jpeg")}" alt="同一连续仿真的八个时间点，包含全景、手部近景和测量字幕"><p>同一实际 episode 的双视角逐帧同步，未拼接阶段。法向力来自原生接触对，240 Hz物理步、八步均值；制动容量是校准参数，不是实测导轨力。字幕使用真值仅作评估，控制器不读取运行中的物体、滑块或接触真值。</p></details></section>'
        blocks.append(body)
    text=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wuji 承托与持续压紧</title><style>body{{font:17px/1.65 system-ui,sans-serif;color:#172333;background:#edf2f5;margin:0}}main{{max-width:1100px;margin:auto;padding:28px}}section,header{{background:white;padding:24px;margin-bottom:22px;border-radius:12px}}h1{{font-size:28px}}h2{{font-size:23px}}video,img{{width:100%;height:auto;background:#111}}a{{color:#155e94}}summary{{cursor:pointer}}.status{{color:#795616;background:#fff3d7;padding:12px;border-radius:6px}}code{{font-size:14px}}</style><main><header><h1>G2 + Wuji：承托、持续压紧与带阻力伸缩</h1><p class="status">{html.escape(a.stage)}</p><p>已做成桌缘取刀到两轮伸缩的完整仿真；当前最强例包含凸起变化与执行延迟。必要联合泛化正在训练，新独立检查尚未开始，真机未运行。</p><p>刀柄主体135×16×12 mm，厚度不含滑块凸起，无解锁按键。取刀采用既有离线规划/脚本，操作采用同一P50权重、滚动参考和明确带误差的初始估计。当前估计来自合成观测，真实视觉尚未接通。</p></header>{''.join(blocks)}<section><h2>承托与剩余阻塞</h2><p>主线保留食指、中指、小指承托。无名指实际承担过反力，但成功候选中均值仅约0.015 N、接触间歇，尚无明确收益。所有手指碰撞保留。</p><p>更强预压档测得操作均值约1.18 N，但刀身转动越界，因此不继续加偏置。约1 N是当前已展示的工作水平，不是全局上限，更不是硬件能力。</p><p>14 mm刀柄、两个联合几何条件和凸起+1 mm的较高模型负载开发例已通过；整个尺寸/位置/摩擦/噪声族仍未完成验证。四张H200在64个联合训练资产上推进，几何范围为长130–140、宽14–18、厚10–14 mm，滑块轴向±5 mm、横向/凸起高度±1 mm。</p><p>本轮修正了旧显式负载的数值能量注入。当前采用有限容量、零速度的被动导轨制动；起动/槽位项为耗散障碍，与旧势阱模型分开。0.2/0.2与0.5/0.5 N是模型幅度，不是实物阻力或上限。摩擦切向合力仍未直接恢复。</p><p><a href="https://github.com/Jr-kelly/artgym/tree/feat/wuji-support-pressure-20261003">本轮代码分支</a> · <a href="https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-continuous-knife-robust-20261003-v1">复用权重和大资产的旧Release</a></p></section></main></html>'''
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text);print(json.dumps({'output':str(a.output),'bytes':a.output.stat().st_size,'embedded_actual_videos':len(episodes),'phase_stitching':False}))
if __name__=='__main__':main()
