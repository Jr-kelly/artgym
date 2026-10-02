"""Report only completed training/dev/confirmation; incomplete final is explicit."""
import csv,json
from scripts.record_wuji_width_goal import R,D,record
B=R/'runs/width-student-distillation-20261002/analysis'
ROLES=['P','C','G','C_endpoint','G_endpoint','teacher']
NAMES=['P','C800','G800','C3200（冻结主候选）','G3200','teacher']
def cell(j,g,m,p,s):return next(c for c in j['cells'] if (c['geometry'],c['model'],c['protocol'],c['source'])==(g,m,p,s))
def kn(c,key='joint_success'):return str(c[key]['k'])+'/'+str(c['n'])
def main():
 c=json.loads((B/'complete-confirm-v1/report.json').read_text());dev=json.loads((B/'window1-complete-dev-v1/report.json').read_text());rep={s:json.loads((B/('repeat%d-dev-v1'%s)/'report.json').read_text()) for s in [52000,52800,54400]};res=json.loads((D/'FINAL_RESOURCES.json').read_text())
 rows=[]
 for phase,j in [('confirmation',c),('pair1-dev',dev)]+[('pair2-dev-'+str(s),j) for s,j in rep.items()]:
  for x in j['cells']:
   for metric in ['success','body_stable','joint_success']:
    m=x[metric];rows.append(dict(phase=phase,geometry=x['geometry'],source=x['source'],model=x['model'],protocol=x['protocol'],metric=metric,k=m['k'],n=m['n'],rate=m['rate'],wilson95_low=m['wilson95'][0],wilson95_high=m['wilson95'][1]))
 with (D/'ALL_COMPLETED_CELL_METRICS.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 lines=['# Wuji宽度蒸馏：两随机流训练/确认结果，最终评测因连接中断待续','',
 '**已真实训练，Goal未完成。** 两个新优化随机流的C/G均完成51200→54400，各臂3200更新/3276800transition，共12800正式Adam更新、13107200新transition；全部12个encoder/Adam/RNG checkpoint已取回并审计。完成126个dev和54个confirmation策略任务，独立复算29880episode；没有把跨模型、协议、检查点复用的初态算作新独立样本。第二组仅作dev重复，首组经独立confirmation。','',
 '最终矩阵及主候选已冻结并打开，但2026-10-02约10:10UTC，8个运行中作业同时收到remote host closed connection，随后17314端点认证前超时。**0个最终任务计入有效统计、8个执行状态待对账、82个未启动。** 未见W115和W115+T110只有已登记静态/结构结果，没有policy泛化结论。不能把中断归为模型失败，也不能声称已完成最终评测。final-freeze.json原模型/状态/阈值不变，恢复后只续接这个矩阵，不重训或重选模型。','',
 '## 目前可支持的研究结论','',
 '加宽训练加速早期F开合与稳定持刀学习，但效果依赖优化随机流，固定3200更新的C可以追上，G晚期出现负迁移。首组800更新新dev的W120来源3联合G29/32、C1/32、P1/32；第二组G31/32、C18/32。第二组1600更新均30/32，3200更新C29/32、G21/32；baseline来源1的第二组3200为C29/32、G15/32（P26/32）。不能把续训本身收益全部包装成几何分布收益，也不能宣称无限续训会解决遗忘。','',
 '首组G3200 baseline来源1独立确认39/64，P61/64，负迁移已确认。G800在该confirmation为60/64，P61/64，早期开发集上的保留担忧没有可信复现。按事先优先baseline保留的规则，主候选冻结为**C3200**：baseline F各来源64/63/64/63（各64），W120来源3联合53/61；G800相应62/60/64/58和56/61。C3200比G800更好保留多项baseline精度，但并非完全保留：C3200 baseline S2来源1为54/64，P62/64。确认差值和配对区间不能当作final验证。','',
 '## 独立confirmation主指标（不是最终集）','',
 'F40秒至少一次open-close，且全程刀身平移<10mm、旋转<0.25rad及有效存活。开合与稳定分别计分，联合为交集。F换向使用仿真slider到位真值，不能证明无传感器自主到位检测。','',
 '| W120来源3 | 开合 | 全程稳定 | 联合 | 联合Wilson95 |','|---|---:|---:|---:|---|']
 for r,n in zip(ROLES,NAMES):
  x=cell(c,'W120',r,'F',3);lines.append('| '+n+' | '+kn(x,'success')+' | '+kn(x,'body_stable')+' | '+kn(x)+' | ['+', '.join('%.1f%%'%(v*100) for v in x['joint_success']['wilson95'])+'] |')
 lines+=['','| W120来源3配对（右−左） | 双成功 | 仅左 | 仅右 | 双失败 | 差值及episode bootstrap95 |','|---|---:|---:|---:|---:|---|']
 for p in c['paired']:
  if (p['geometry'],p['source'],p['protocol'])==('W120',3,'F') and (p['left'],p['right']) in [('C','G'),('G','P'),('C_endpoint','G'),('C_endpoint','G_endpoint')]:
   m=p['joint_success'];lines.append('| '+p['right']+' − '+p['left']+' | '+' | '.join(str(m[k]) for k in ['both_success','left_only','right_only','both_fail'])+' | %.1f%% [%s] |'%(m['right_minus_left']*100,', '.join('%.1f%%'%(v*100) for v in m['paired_bootstrap95'])))
 lines+=['','## 全来源confirmation，不以总体均值掩盖失败','', 'F每格“开合/稳定/联合；n”。S2/S5每格为全部严格阶段通过及全程稳定的真实分子/分母；20秒、固定2/5秒换向、阶段末9点误差<2mm。F进步不等于严格精度进步。','']
 for proto in ['F','S2','S5']:
  lines+=['### '+proto,'','| 几何/来源 | '+' | '.join(NAMES)+' |','|---|'+'---:|'*6]
  for g in ['baseline','W110','W120']:
   for source in range(4):
    xs=[cell(c,g,r,proto,source) for r in ROLES];values=['%d/%d/%d；n=%d'%(x['success']['k'],x['body_stable']['k'],x['joint_success']['k'],x['n']) if proto=='F' else kn(x,'success') for x in xs];lines.append('| '+g+'/'+str(source)+' | '+' | '.join(values)+' |')
  lines+=['']
 lines+=['## 两组优化随机流的匹配新dev趋势','', '| 新增更新 | 首组C/G W120来源3 | 重复C/G W120来源3 | 首组C/G baseline来源1 | 重复C/G baseline来源1 |','|---:|---:|---:|---:|---:|']
 for step in [52000,52800,54400]:
  v=[]
  for g,source in [('W120',3),('baseline',1)]:
   v.extend([' / '.join(kn(cell(dev,g,a+str(step),'F',source)) for a in ['C','G']),' / '.join(kn(cell(rep[step],g,a,'F',source)) for a in ['C','G'])])
  lines.append('| '+str(step-51200)+' | '+' | '.join(v)+' |')
 lines+=['', '两次重复从同一预训练SA51200出发，seed2026100215/16；不是从零独立训练。episode Wilson和bootstrap只刻画固定模型在登记初态中的行为，不能用两优化seed保证所有随机流的效果。选择靠行为，不靠loss。第二组因早期独立confirmation证明明确收益且预算充足而执行，未追加任何后续窗口。','',
 '## 合同、数据和失败原因边界','',
 '仅SC-real student encoder更新，actor/teacher encoder/共享normalizer冻结。实际Adam恢复parent moments，lr3e-4、betas(.9,.999)、eps1e-8、无weight decay/scheduler；loss=latent MSE +25×executed target MSE/(.04rad)^2，原straight-through梯度。绝对step恢复51200，teacher mixing为0。20秒训练horizon及30Hz原控制保持；相同incomingRNN/当前控制记忆的监督forward不推进真实RNN。','',
 '256环境×4步；逻辑组128/64/64，来源逐槽位匹配。组0各32，组1/2为22/21/0/21。C三组实际baseline，G为baseline/W110/W120；宽度source2不用于新增teacher监督，但所有正式评测保留。policy输入2076=history2000+初始校准55+已知controller21，metadata不入policy，不路由专家或失败接管。实际transition/reset计数和所有12个optimizer/RNG/冻结哈希见PAIR1/PAIR2_ALL_CHECKPOINT_AUDIT。','',
 '所有主统计同H200。零变化原路径/多资产C同初态256环境×8步差0，teacher latent/冻结actor同输入与incomingRNN一致，bbox/hand_base/索引/PhysX有效惯量验证通过。可丢弃副本68真实更新/69632transition，仅技术预检，禁止作为科学起点或候选。首对源码公共02749e10（225473d1…），第二组及后续评测公共dba402c2（a1739e7c…）；差异只有static构造器和queue映射，trainer/任务/controller/evaluator相同。逐作业source pin/模型/数据/资产/设备UUID和有限timeout均保存。','',
 '新数据四split seed2026100211/12/13/14，共11776尝试状态，允许训练10池各256有效状态、共2560，C引用baseline不重复计数。旧final数组始终关闭。静态接受依据原2秒、关节/穿透代理/漂移/旋转/thumb IK阈值及固定顺序，不看policy表现、不padding。最终5几何已预登记：baseline512、W110477、W120474、W115251、组合246，source3分母128/93/90/59/54。计划90任务/35280episode，但均未形成可计入最终结果的完整收据。','',
 '前后20秒、首次失稳、open/close失败和cycle数均在逐episode原始复算中保留，学习曲线和loss诊断见figures。遗忘与40秒后半程失败不能证明20秒horizon是根因；恢复/优化/输入/标签执行链路未发现具体错误，teacher在learner访问状态中的可靠性和观测限制仍未确定。不能用一次失败宣称纯proprioception不可能。','',
 '保留实现失败：缺失历史small.npy使第一dev队列18作业及静态首2作业失败，改为构造时使用相应登记新状态后各一次重试成功；失败目录/消耗保留。RTX双仿真同进程signal11改为独立进程。旧端口33024认证前超时，新17314曾恢复，现在也超时；8个final作业是transport未知，不能归为policy失败，也不能确认实例停机原因。','',
 '## 真实视频与资源账本','',
 '12段预先固定新dev source3首有效状态，baseline/W120各6模型。RTX4090/batch1相机重模拟与H200批量统计分开。W120 P于6.2秒、C800于1.8秒、主C3200于23.7秒结束，G800完成40秒；全部失败保留，没有换成功状态。对比视频中结束片段只保持末帧，显著红字ENDED；没有伪造后续物理演示。没有真机或sim2real结果。','',
 '原累计%.8fGPUh，已确认本轮新增**%.8fGPUh**，已确认累计**%.8fGPUh**。8个远端未知作业暂按每个630秒记**1.4GPUh**，因此账本暂计**%.8f/64GPUh**、保守剩余**%.8fGPUh**；待恢复后从execution.json对账，不能把暂记值说成精确实耗。峰值跨机器8GPU。'%(res['historical_gpu_hours'],res['known_new_gpu_hours'],res['known_cumulative_gpu_hours'],res['cumulative_gpu_hours'],res['remaining_gpu_hours']),'',
 'NVML覆盖109.01分钟（08:20:33—10:09:33UTC），该覆盖期整机平均43.25%；未知时段按0的四小时估计19.64%，**未证实满足26%门槛**，且不能确认是否因此停机。没有填充耗作业。已核验PID/start_ticks并停止本轮利用率监控；本地GPU作业/控制器已结束，ToDesk与其他任务保留；远端8作业未能核实终止，仅有限timeout已登记。','',
 '[本轮分支](https://github.com/Jr-kelly/artgym/tree/feat/wuji-width-student-distillation-20261002)；[训练/确认/视频Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-width-student-distillation-20261002-v1)。该版本明确final待续，准备和旧几何Release保留。checkpoint、raw dev/confirmation、实际失败/未知收据、图和视频均独立发布并核对服务器SHA。关键新checkpoint/新静态数据恢复通过，父模型按旧Release及固定SHA引用，不重跑历史恢复。','',
 '当前唯一必要下一步：恢复授权H200端点，先对账8个未知execution收据，再继续同一冻结最终矩阵。研究后续首要问题是严格定时到位精度的保留，先作单变量时序/同incomingRNN执行目标误差诊断；不要盲目延长宽度训练。']
 (D/'FINAL_REPORT.md').write_text('\n'.join(lines)+'\n')
 status=dict(goal_complete=False,formal_training_complete=True,formal_updates=12800,formal_transitions=13107200,all_saved_checkpoints=12,completed_dev_runs=126,completed_confirmation_runs=54,valid_rescored_episodes=29880,final_complete=False,final_complete_tasks=0,final_unknown_tasks=8,final_pending_tasks=82,heldout_policy_results_available=False,selected_main='C_endpoint',candidate_selection_unchanged=True,current_blocker='Authorized17314SSHendpointtimedoutafterall8connectionsclosedbyremotehost',exact_remote_consumption_unknown=True,resources=res)
 (D/'DELIVERY_STATUS.json').write_text(json.dumps(status,indent=2)+'\n')
 record('completed_training_confirmation_report_and_final_blocker_written',evidence='research/width-student-distillation-20261002/FINAL_REPORT.md',next='Deliver all completed science; recover endpoint for unchanged frozen final, no trainingrestart')
if __name__=='__main__':main()
