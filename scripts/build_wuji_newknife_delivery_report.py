"""Build a browsable evidence report from explicit final selection and trial paths."""
import argparse,html,json,shutil
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True)
 result=json.loads(a.results.read_text());esc=html.escape;rows=[]
 for entry in result['trials']:
  path=Path(entry['trial'])/'newknife-evaluation.json'
  if not path.exists():
   rows.append('<tr><td>'+esc(entry['label'])+'</td><td>'+esc(entry['role'])+'</td><td colspan="5">'+esc(entry.get('failure','No completed native evaluation'))+'</td></tr>');continue
  e=json.loads(path.read_text());mm=lambda key:' / '.join('%.2f'%(v*1000) for v in e[key]);failed=', '.join(k for k,v in e['checks'].items() if not v)
  rows.append('<tr>'+''.join('<td>'+esc(str(v))+'</td>' for v in [entry['label'],entry['role'],mm('forward_displacement_m'),mm('endpoints_relative_initial_m'),'%.1f%%'%(100*e['effective_cap_contact_fraction']),'%.3f'%e['old_rotation_rad'],'PASS' if e['pass_all'] else failed])+'</tr>')
 for name in ['asset-contact-geometry.png','resistance-calibration.png']:
  shutil.copy2(Path('research/newknife-20261005')/name,a.output/name)
 for name,source in result['videos'].items():shutil.copy2(source,a.output/name)
 status='完整任务通过' if result['functional_demo_ready'] else '任务尚未通过：保留最强候选和完整失败过程'
 text='''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wuji 新刀连续操作证据</title><style>body{font:17px/1.6 system-ui,sans-serif;max-width:1250px;margin:32px auto;padding:0 22px;background:#111923;color:#e5edf5}h1,h2{line-height:1.25}a{color:#79d4f1}video,img{max-width:100%;height:auto}table{border-collapse:collapse;font-size:14px;width:100%}th,td{border:1px solid #44515e;padding:9px;text-align:left}code{overflow-wrap:anywhere}.status{padding:18px;background:#263548;border-left:5px solid #edbe76}.scroll{overflow:auto}</style><h1>G2＋Wuji 新刀连续操作</h1>'''
 text+='<p class="status">'+esc(status)+'</p><p>'+esc(result['summary'])+'</p>'
 text+='<h2>完整连续视频</h2><p>同一仿真过程：桌缘取刀、离桌承托、两轮 35 mm 命令与回收。双视角同步，36 秒，无成功片段拼接。曲线是离线记录的实际位移；制动容量是模型值。</p><video controls preload="metadata" src="selected-synchronized.mp4"></video><p><a href="selected-full-scene.mp4">原始全景 MP4</a> · <a href="selected-closeup.mp4">原始近景 MP4</a></p>'
 text+='<h2>相同任务下的结果</h2><p>两轮实际前移各须 ≥30 mm；伸出端点相对初始为 30–40 mm，回收残差绝对值 ≤5 mm。接触、离桌、姿态与保持指标不改。第二轮行程单独扣除其真实起点。</p><div class="scroll"><table><tr><th>案例</th><th>证据角色</th><th>两轮实际前移 mm</th><th>四端点 mm</th><th>有效滑块接触</th><th>旋转 rad</th><th>结果／未通过项</th></tr>'+''.join(rows)+'</table></div>'
 text+='<h2>资产与阻力</h2><p>144×19×8 mm 主体，32×7×2 mm 凸起滑块，总厚 10 mm、总质量 55 g。主体厚度由总厚推算；内部结构、质量分配、惯量和轨道极限为明确工程假设。无现成可用本地 Hunyuan 工作流，采用实测约束的参数化 URDF 与分离运动组件。</p><img src="asset-contact-geometry.png" alt="新刀接触几何与尺寸"><p>75 gf＝0.73549875 N，约束轴向阻力量级，不是拇指法向压力。恒容量参考与最小被动变化模型分开报告。固定刀身的隔离加载只用于标定，完整任务撤去固定和外加力。法向接触记录、模型容量、实际位移与缺测的轴向总接触力／导轨反力严格分开。</p><img src="resistance-calibration.png" alt="隔离阻力校准">'
 text+='<h2>实现、复现与边界</h2><ul>'+''.join('<li>'+esc(s)+'</li>' for s in result['conclusions'])+'</ul><p>公开材料仅含代码参数、仿真渲染与派生证据；不包含私人照片或原始 Goal。没有下发真实机器人运动命令。</p><pre><code>python -m scripts.run_wuji_newknife_selected --output runs/newknife-reproduction</code></pre><p>依赖、恢复归档哈希与一次空目录复现记录见同版本 REPRODUCE.md 和 RESTORE-RESULT.json。训练拟合、开发比较、冻结验证与真机证据分别记录。</p></html>'
 (a.output/'index.html').write_text(text);shutil.copy2(a.results,a.output/'delivery-results.json');print(a.output/'index.html')
if __name__=='__main__':main()
