"""Build a browsable, evidence-linked report without changing scoring."""
import html,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'research/highload-20261005';B=R/'runs/highload-20261005';TAG='wuji-g2-highload-20261005-v1';URL='https://github.com/Jr-kelly/artgym/releases/download/'+TAG+'/'
def main():
 result=json.loads((D/'DELIVERY-RESULTS.json').read_text());rows=result['trials'];table=[]
 old=[('V13 主刀 .35',R/'runs/traction-20261005/selected-full-video-v13/simulation'),('V13 fresh01 .35',R/'runs/traction-20261005/validation/fresh01-v15/simulation'),('V13 薄刀 .35',R/'runs/traction-20261005/validation/selected-thin035-v13/simulation')]
 for label,p in old:
  e=json.loads((p/'functional-evaluation.json').read_text());table.append((label,e,str(p.relative_to(R))))
 keys=['tracking1-threecycle-video-v1','fresh01-development035-v1/simulation','thin-development035-v1/simulation','selected-fresh01-video-v10/simulation','tracking1-load020-added0.05-video-v3','tracking1-load050-added0.05-v1','tracking1-load050-added0.10-v1','unseen05-frozen-v10/simulation','unseen06-frozen-v10/simulation']
 for key in keys:
  for row in rows:
   if row['trial'].endswith(key):table.append((key,row['evaluation'],row['trial']))
 md=['| 条件 | 伸1 / 回1 / 伸2 / 回2 mm | 峰值 rad | 跨轮 rad | 拇指接触 | 原评分 |','|---|---|---:|---:|---:|---|']
 for label,e,p in table:
  endpoints=' / '.join('%.2f'%(1000*v) for v in e['slider_endpoints_m'].values());failed=', '.join(k for k,v in e['checks'].items() if not v)
  md.append('| '+label+' | '+endpoints+' | %.3f | %.3f | %.3f | '%(e['relative_max_rotation_rad'],e['return_to_return_rotation_rad'],e['thumb_contact_substep_fraction'])+('通过' if e['continuous_pickup_demo_pass'] else '失败：'+failed)+' |')
 text='''# G2 + Wuji 高阻力双向操作：能力证据与持续性边界

本轮保留 V13 的 .35 完整通过基线，交付 tracking1 工程候选、共同初始几何适配、完整视频、可恢复配置及新增已知负载能力证据。新候选并未通过所有原评分，必要泛化和真机就绪仍未完成。无新训练，S120 权重保持 ad16a153c27eb01567c14422ca8ed23e5bebfc6e1c901683031f245631944d2a；这是学习承托与显式关节反馈拇指控制的组合。

## 行为结论

原 .5 候选的峰值出现在约18.07、28.13秒，主要绕刀长轴滚转；长轴方向倾斜仅约 .045rad。峰值时拇指及食指、中指、小指承托接触保持，距端挡仍有余量。FK 轴向线性化与精确关节 FK 的差约1mm，不能支持“坐标失真或推力不足是唯一主因”。这些是诊断，在线控制没有读取刀体、滑块、接触或负载真值。

连续第三轮揭示了实际边界：前两轮30.04/2.85和30.98/6.15mm，第三轮只伸20.74mm，第三回缩段接触均值约.884，最终相对转角约.600rad。因此不能把前两轮回位解释为可持续稳定。46秒原始全轨迹评分保留；另存原样前36秒评分仅用于区分两轮任务与第三轮诊断，不改阈值、不改原始全轨迹失败。

联合变化有实际行程收益：fresh01从 V13 第二伸22.55mm提高至 tracking1 的31.63mm；薄刀 .35 达35.73/3.02/36.36/2.80mm。但姿态包络仍失败。fresh01–04本轮是开发条件，012–015仍为旧几何留出，未用于拟合。新 unseen05/06 在最终候选冻结后声明，结果未用于调参；两个合成条件不能代表成功率或真实传感噪声标定。

## 匹配证据

端点是距导轨下限的位置，回缩数字是剩余位置；命令始终40mm。每段真实有符号位移、转动时刻及接触见 DELIVERY-RESULTS.json 的 diagnostics。仿真剩余<8mm不等于实物刀片完全收起。

'''+ '\n'.join(md)+'''

## 实施及淘汰的路线

- 轴向补偿时序、低通和末段保持：个别峰值下降，但联合变化第二轮行程或稳定性退化；未采用。
- 按换向/伸出重新估计静态关节偏差：没有改善第三轮，出现接近零行程；未采用。
- 横向展开承托位置：小展开通过主刀73点取刀及81点完整行程证书，但第二回缩剩15–19mm；两个几何适配与大展开在原碰撞证书处被拒绝，未冒充物理失败或绕过证书。
- 压力修正耦合：操作期冻结已有预压、全程纯法向、只在操作期纯法向均已实现与运行。最后一个保留逐帧相同取刀前缀，早期滚转变小，但第三回缩反向移至42.14mm，漂移及保持失败。不能仅据较小转角选它。

新增可选实现默认关闭，原控制器默认行为不变。Native/CPU冻结检查、操作前缀完全一致检查见 PRESSURE-CHECK-V7.json 和 PRESSURE-PREFIX-PARITY-V8.json。evaluate_wuji_antirotation.py只增加跨机器资产路径解析，criterion常量、比较符与时间窗未变。本轮未发现值得追加预算的稳定协调路径，因此未原样延长训练。

## 新增已知负载能力

在 .20 原被动制动基础容量及原起动/沿程调制之上，全操作期施加额外 .05N 平衡对向测试载荷，完整两轮通过全部原评分，端点34.22/.59/34.42/1.39mm。240Hz记录验证激活覆盖及方向；滑块与刀体施加相反力并平衡力矩，没有净夹持或助推。载荷反向滑移时可做少量正功，但只会远离当段目标；净功约−.006789J，正向错误运动功约.000116J。

这是指定仿真任务的附加载荷能力下界，不是总阻力 .25N、实刀测得推力或最大能力。与 .50 容量叠加 .05N时第二回缩10.09mm失败；叠加 .10N时第二伸仅4.36mm。原刀轴向总接触力B和导轨反力C仍为null，法向A和容量配置不能代替它们，端挡峰值未用作持续推力。

## 复现与视频

入口：`python -m scripts.run_wuji_highload_selected --mode highload --output <新目录>`。模式 baseline保留V13，capacity复现新增完整负载演示。共同几何机制通过 --initial-estimate 和仅供仿真的 --knife-asset 接入；恢复依赖、哈希及环境见 REPRODUCE.md。

完整主视角/近景同步视频：highload050-three-cycles.mp4（46秒，保留失败）、capacity020-plus005.mp4（36秒）。几何变化完整原片另提供。可浏览报告 highload-report.html；原始MP4、轨迹和240Hz测量另存Release，私人附件未发布。

## 证据范围与下一步

源码/资产证书、学习承托旧权重、开发仿真、冻结后联合验证、空目录复现、完整脚本演示分别记录；本轮没有真机运行或新拟合结果。可复用的新证据确定了“高阻重复操作后接触/落座协调失效”的具体行为边界，但没有证明单一机械主因。下一次应基于原刀双向起动峰值、沿程阻力、有效行程与完全收起位置收紧模型，并检验稳定承托协调；真实SDK仍需核对关节映射、单位、时间戳、延迟和位置响应。沿用 research/wrap-force-20261004/REAL-MEASUREMENT.md 与既有格式，不新增表格。未下发真机指令。

状态：V13功能基线和新增容量演示可运行；新 .5 工程候选原评分未全过。necessary_generalization_resolved=false，axial_force_measurement_resolved=false，hardware_ready=false，real_robot_ran=false，goal_complete=false。delivery_complete只表示本轮交付完成。
'''
 resources={}
 for name in ['local','development']:
  p=B/'resources'/name/'status.json'
  if p.exists():
   s=json.loads(p.read_text());w=s['windows']['14400'];resources[name]=s
   text+='\n资源 '+name+'：截至 '+s['heartbeat']+'，已观测 %.1f分钟，整机均值%.2f%%；不足四小时，不能宣称完整四小时合规。\n'%(w['covered_seconds']/60,w['mean_percent'])
 text+='\n远端本轮低于26%门槛；预处理、诊断与归档期间存在空闲。未运行填充作业，原用户进程保留。\n'
 (D/'FINAL-REPORT.md').write_text(text)
 (D/'RESOURCE-SUMMARY.json').write_text(json.dumps(resources,indent=2))
 body='<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Wuji 高阻力交付</title><style>body{max-width:1100px;margin:30px auto;padding:20px;font:17px/1.7 system-ui;background:#f7f8fa;color:#172130}video,img{width:100%}pre{white-space:pre-wrap}a{color:#0759ad}</style><h1>G2 + Wuji 高阻力双向操作</h1><p>完整仿真、原评分、明确失败边界。不是实刀推力或真机结果。</p>'
 for title,name in [('完整 .5 三轮（保留衰减失败）','highload050-three-cycles.mp4'),('完整 .20＋.05N 对向附加载荷（通过）','capacity020-plus005.mp4'),('fresh01 .35 共同几何适配，完整主视角','fresh01-continuous.mp4'),('fresh01 .35 完整近景','fresh01-closeup.mp4')]:body+='<h2>'+title+'</h2><video controls preload="metadata" src="'+URL+name+'"></video><p><a href="'+URL+name+'">下载原MP4</a></p>'
 body+='<h2>完整结果与范围</h2><pre>'+html.escape(text)+'</pre><p><a href="'+URL+'DELIVERY-RESULTS.json">原始数值索引</a> · <a href="'+URL+'highload-evidence.tar.gz">轨迹和测量</a></p></html>'
 (B/'media/highload-report.html').write_text(body)
 print(D/'FINAL-REPORT.md')
if __name__=='__main__':main()
