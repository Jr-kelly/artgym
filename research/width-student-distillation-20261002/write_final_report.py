"""Write all-source tables from frozen, independently rescored scientific evidence."""
import csv,json,statistics
from pathlib import Path
from scripts.record_wuji_width_goal import R,D,record
from scripts.wuji_width_contract import sha
BASE=R/'runs/width-student-distillation-20261002/analysis'
ROLES=['P','C','G','C_endpoint','G_endpoint','teacher']
NAMES=['P','C800','G800','C3200（主）','G3200','teacher']
def cell(j,g,m,p,s):return next(c for c in j['cells'] if (c['geometry'],c['model'],c['protocol'],c['source'])==(g,m,p,s))
def count(c,key='joint_success'):return str(c[key]['k'])+'/'+str(c['n'])
def interval(m):return '['+', '.join('%.1f%%'%(100*x) for x in m['wilson95'])+']'
def main():
 s=json.loads((D/'STATE.json').read_text());assert s['final_evaluation_complete'] and s['optimizer_updates']==12800
 freeze=json.loads((D/'final-freeze.json').read_text());assert freeze['selected_main']=='C_endpoint'
 final=json.loads((BASE/'frozen-final-v1/report.json').read_text());confirm=json.loads((BASE/'complete-confirm-v1/report.json').read_text())
 dev=json.loads((BASE/'window1-complete-dev-v1/report.json').read_text());rep={step:json.loads((BASE/('repeat%d-dev-v1'%step)/'report.json').read_text()) for step in [52000,52800,54400]}
 res=json.loads((D/'FINAL_RESOURCES.json').read_text());episodes=list(csv.DictReader((BASE/'frozen-final-v1/episodes.csv').open()))
 assert len(final['cells'])==360 and len(episodes)==freeze['episodes']==35280
 flat=[]
 for phase,j in [('final',final),('confirmation',confirm),('first_pair_dev',dev)]+[('repeat_dev_'+str(step),j) for step,j in rep.items()]:
  for c in j['cells']:
   for metric in ['success','body_stable','joint_success']:
    m=c[metric];flat.append(dict(phase=phase,geometry=c['geometry'],source=c['source'],model=c['model'],protocol=c['protocol'],metric=metric,k=m['k'],n=m['n'],rate=m['rate'],wilson95_low=m['wilson95'][0],wilson95_high=m['wilson95'][1]))
 with (D/'ALL_CELL_METRICS.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
 lines=['# Wuji 跨宽度 student 蒸馏：配对训练与冻结最终结果','',
 '两组新优化随机流各完成C/G同父模型、同预算的3200更新；共 **12,800次真实Adam更新、13,107,200个新transition**。没有第二/第三续训窗口，绝对终点均为54400。P未更新。第二随机流只作新dev重复，第一随机流进入独立confirmation和final；这不是两次从零独立训练，也不是两组都通过最终集。','',
 '宽度训练的主要证据是早期学习更快：第一组800更新新dev的W120来源3联合G29/32、C1/32、P1/32，第二组为G31/32、C18/32；1600更新时第二组两者均30/32。固定3200终点原尺寸C也获得宽刀能力，因此不能把所有后期收益归因于宽度扩展。第一组G3200的baseline来源1独立确认39/64，P61/64，出现负迁移。','',
 '按打开final前冻结的“优先baseline保留”规则，**主候选是C3200**。它在confirmation的baseline F为64/63/64/63（各64），W120来源3为53/61；G800相应为62/60/64/58和56/61。C3200也比G800更好保留baseline严格到位精度。仍保留G800及同800预算C、两个固定3200终点、P和teacher，避免只展示有利检查点。最终结果没有用于重选模型、抓姿或阈值。','',
 '最终F证据：G800的W120来源3联合78/90（P5/90、同预算C8003/90），未见W115与组合条件来源3分别54/59、49/54（P3/59、4/54）。G3200虽在W120达到81/90，却在baseline来源1降至50/128（P107/128，G800117/128），确认负迁移。冻结主C3200相应W120为72/90、baseline来源1为119/128，未见来源3为53/59、49/54；但组合来源1为57/64而P64/64。G800也有W110来源0的121/128对P128/128等局部退化。结论是早期扩大宽度覆盖有明确收益，长期扩大并非持续更优，且无法声称所有来源/指标均保留。','',
 '严格到位仍未解决：W120来源3的G800在S2和S5均为0/90，主C3200分别13/90、3/90，teacher为49/90、31/90。G800还将baseline来源0的S2从P124/128降至71/128，将W120来源2的S5从118/128降至26/128。主C3200也有baseline来源3 S5从98/128降至81/128的代价。因此F40秒的开合/持刀改善不等于精密定时到位能力保留。','',
 '## 冻结最终主结果','',
 'F要求40秒内至少完成一次开合，并单列全程持刀稳定；联合是二者交集。稳定阈值平移<10mm、旋转<0.25rad，含有效性/存活要求。F换向使用仿真slider到位真值（10mm、连续45步），不能证明无传感器自主到位检测。','',
 '| W120来源3模型 | 开合 | 全程稳定 | 联合 | 联合Wilson95 |','|---|---:|---:|---:|---|']
 for role,name in zip(ROLES,NAMES):
  c=cell(final,'W120',role,'F',3);lines.append('| '+name+' | '+count(c,'success')+' | '+count(c,'body_stable')+' | '+count(c)+' | '+interval(c['joint_success'])+' |')
 lines+=['','配对四格与差值（同初态，区间为4000次episode配对bootstrap；多单元比较是描述性结果，未作多重检验校正）：','', '| 比较（右−左） | 双成功 | 仅左 | 仅右 | 双失败 | 差值 / 95% |','|---|---:|---:|---:|---:|---|']
 for pair in final['paired']:
  if pair['geometry']=='W120' and pair['source']==3 and pair['protocol']=='F' and (pair['left'],pair['right']) in [('C','G'),('G','P'),('C_endpoint','P'),('C_endpoint','G_endpoint')]:
   m=pair['joint_success'];ci=', '.join('%.1f%%'%(100*x) for x in m['paired_bootstrap95']);lines.append('| '+pair['right']+' − '+pair['left']+' | '+' | '.join(str(m[k]) for k in ['both_success','left_only','right_only','both_fail'])+' | %.1f%% / [%s] |'%(100*m['right_minus_left'],ci))
 lines+=['','## 所有几何和来源的F结果','', '每格为“开合 / 全程稳定 / 联合；分母”。baseline保留、W110/W120来源2和未见条件均保留，不能用总体平均掩盖失败。','', '| 几何/来源 | '+' | '.join(NAMES)+' |','|---|'+'---:|'*6]
 for g in ['baseline','W110','W120','W115','W115_T110']:
  for source in range(4):
   cs=[cell(final,g,r,'F',source) for r in ROLES];values=['%d / %d / %d；n=%d'%(c['success']['k'],c['body_stable']['k'],c['joint_success']['k'],c['n']) for c in cs];lines.append('| '+g+'/'+str(source)+' | '+' | '.join(values)+' |')
 lines+=['','W115为147×21.85×8mm插值条件；W115+T110为147×21.85×8.8mm组合条件，两者均未进入训练或候选选择。它们仅在final前做无policy静态验收。所有尺寸保持质量、PhysX实际有效惯量及导轨/滑块/摩擦/控制参数。统计仅覆盖已静态有效、原四类抓姿附近的新扰动状态，不能声称任意抓姿、连续尺寸范围或真机泛化。','', '## 严格定时到位的限制','', 'S2/S5分别每2/5秒固定换向，总20秒，每阶段末9点误差<2mm且全程稳定有效。其success本身已包含稳定门槛。F提升不能替代严格精度提升。','']
 for protocol in ['S2','S5']:
  lines+=['### '+protocol,'','| 几何/来源 | '+' | '.join(NAMES)+' |','|---|'+'---:|'*6]
  for g in ['baseline','W110','W120','W115','W115_T110']:
   for source in range(4):lines.append('| '+g+'/'+str(source)+' | '+' | '.join(count(cell(final,g,r,protocol,source),'success') for r in ROLES)+' |')
  lines+=['']
 lines+=['## 失败时序与原因的证据边界','', '| 条件/模型 | 前20秒稳定 | 后20秒稳定 | 全40秒稳定 | 未完成open | open后无close |','|---|---:|---:|---:|---:|---:|']
 for g,source in [('baseline',1),('W120',3),('W115_T110',3)]:
  for role in ROLES:
   rows=[r for r in episodes if (r['geometry'],int(r['source']),r['model'],r['protocol'])==(g,source,role,'F')];n=len(rows)
   vals=[sum(r[key]=='True' for r in rows) for key in ['holding_first20','holding_last20','body_stable']]+[sum(int(r['open_commands_reached'])==0 for r in rows),sum(int(r['open_commands_reached'])>0 and int(r['close_commands_reached'])==0 for r in rows)]
   lines.append('| '+g+'/'+str(source)+' '+role+' | '+' | '.join(str(x)+'/'+str(n) for x in vals)+' |')
 lines+=['', '完整episode表包含首次越过body阈值时间、位移/转角、open/close到位数、cycle计数，以及完全位于各20秒段内的开合数；不会把跨20秒的开合算作后半段完整开合。首次失稳曲线和loss图见figures。训练horizon保留20秒、F评测40秒，时序关联不能证明horizon是根因。恢复、Adam/LR、controller、bbox和RNN一致性检查通过；仍不能仅凭遗忘确定teacher在learner访问状态中的标签可靠性，也不能宣称纯proprioception不可能。','',
 '## 训练合同、重复与数据隔离','',
 'SC-real单encoder、2076维合法输入：50帧proprio/history2000 + 初始校准55 + 已知controller21。几何/source ID仅作采样元数据，不进入policy；不路由专家，不在失败后接管。仅student encoder更新；冻结actor、teacher encoder和共享normalizer。Adam恢复父moments，实际lr3e-4、betas(.9,.999)、eps1e-8、weight_decay0，无scheduler。latent MSE + 25×executed-target MSE/(.04rad)^2及原straight-through梯度保留。teacher mixing按绝对步数恢复后为0。','',
 '256环境×4rollout=1024transition/update。C/G逐槽位匹配逻辑组128/64/64，来源计数组0为32/32/32/32，组1/2为22/21/0/21。C三组真实几何均baseline，G分别baseline/W110/W120；宽刀source2不作新增teacher监督，但全部评测保留。实际transition配比固定，实际reset次数会随行为不同。PAIR1/PAIR2_ALL_CHECKPOINT_AUDIT.json保存所有12个checkpoint的实际Adam步数、源计数、哈希和RNG；width_reset_counts包含256初始槽位reset，汇总resets字段不含它们。','',
 '新优化seed为2026100215/16，各自从未改动SA51200完整恢复后只播种一次，保存52000/52800/54400。两组之间是不同优化随机流，组内共同父encoder/Adam和初始RNG一致；物理轨迹不声称逐位相同。第二组按首次独立confirmation的明确早期收益和剩余预算条件执行，未用新分布、损失或horizon替换第一组。','', '| 新增更新 | 首对C/G W120来源3 | 重复C/G W120来源3 | 首对C/G baseline来源1 | 重复C/G baseline来源1 |','|---:|---:|---:|---:|---:|']
 for step in [52000,52800,54400]:
  values=[]
  for g,src in [('W120',3),('baseline',1)]:
   values.append(' / '.join(count(cell(dev,g,a+str(step),'F',src)) for a in ['C','G']))
   values.append(' / '.join(count(cell(rep[step],g,a,'F',src)) for a in ['C','G']))
  lines.append('| '+str(step-51200)+' | '+' | '.join([values[0],values[1],values[2],values[3]])+' |')
 lines+=['', '两组优化seed不能支撑对所有优化随机流的总体统计保证；episode区间只量化固定模型在登记初态中的行为。旧teacher/student/geometry final数组全程关闭。新数据train/dev/confirmation/final seed分别2026100211/12/13/14，尝试状态共11776，训练允许10个池各256有效扰动状态、共2560；C重复引用baseline池不计新增独立状态。静态规则沿用2秒持握、原关节/穿透代理/漂移/旋转/局部thumb IK阈值，按固定顺序接受，不看policy表现。','',
 'final共1960个有效初态：baseline512，W110477，W120474，W115251，组合246。对应source3真实分母128/93/90/59/54；拒绝全部保留，没有padding、重复状态补数或因差结果更换条件。6模型×3协议共35280episode，同一初态的多个模型/协议/检查点互相关联，不能计为35280个独立初态。所有360最终cell、Wilson区间、配对四格和逐episode轨迹可重算。','',
 '## 实现、运行源码和保留失败','',
 '首对训练源码为公共提交02749e10、source SHA225473d1931b25a84183347b61c3bd7ac910c100cf531573d498217a3b75e7fa。第二组和后续确认/final为公共dba402c2、source SHAa1739e7c66f61705b0b1d1edbf78c33924fb455d20471a9d35767afa38cd795e。源码A/B仅static构造器和queue覆盖映射发生变化，trainer/任务/控制器/评测代码相同；Git树精确恢复证明见FORMAL_SOURCE_PROVENANCE和SOURCE_B_PROVENANCE。每作业使用独立只读pin，身份含设备UUID、输入/模型/源码哈希和实际有限timeout。','',
 '真实8H200/PyTorch2.1+cu118/IsaacGym-TacSL后端用于全部主统计。同后端teacher latent传入同冻结actor/incomingRNN一致，原路径与零变化多资产C在同状态256环境×8步全部最大差0。H200及RTX可丢弃副本共68实际更新/69632transition，全部禁止进入科学选择。新增宽度多资产bbox、索引、hand_base缓存和PhysX有效惯量实际验证通过。','',
 '保留失败：旧33024端口三轮认证前超时，新17314端点恢复连接；不探测其他历史机器。首次fresh-dev队列18作业及seen静态首2作业因构造器隐式读取不存在的历史small.npy失败；修复为构造时直接引用相应登记新cohort，旧失败目录及消耗保留，重试各只1次。队列发现首个失败停止尚未启动任务。RTX双仿真同进程signal11改为独立进程；CPU只读审计一次torch/Gym导入顺序错误改为不引入Gym，未产生额外GPU工作。未把实现失败当作几何方法失败。','',
 '## 视频、消耗与交付','',
 '12段预登记新dev来源3首有效状态的视频，两个几何各比较6模型。全部原始视频/trace和带标签版本保留；对比视频中已终止片段仅保持最终帧，并显著标红ENDED，未模拟后续。RTX4090/batch1为单独相机重模拟，不替代H200/batch整cohort统计。W120演示中的主C3200于23.7s终止，P于6.2s、C800于1.8s终止；没有按成功换状态。差异同时涉及设备/批大小/初态，不能归因于设备单一因素。没有真机结果或sim2real认证。','',
 '原累计 %.8f GPUh；本轮记账 **%.8f GPUh**；累计保守记账 **%.8f/64 GPUh**，剩余 **%.8f GPUh**。8个被杀停作业仍保留合计1.4 GPUh的timeout上界，精确停止时刻不可恢复，其余按作业实测时长记账。68可丢弃更新与所有失败均记账，峰值同时占用%d张（含跨机器RTX）。'%(res['historical_gpu_hours'],res['new_gpu_hours'],res['cumulative_gpu_hours'],res['remaining_gpu_hours'],res['peak_combined_gpus']),'', '| 类别 | 作业 | 记账GPUh | 失败作业 |','|---|---:|---:|---:|']
 for kind,v in res['categories'].items():lines.append('| '+kind+' | '+str(v['jobs'])+' | %.8f | %d |'%(v['gpu_hours'],v['failed_jobs']))
 u=res['utilization'];lines+=['', 'Goal开始至资源审计墙钟%.1f分钟；四个完整训练循环各约31分钟，两臂并行，未声称8倍单训练加速。主要等待包括早期SSH不可达、配对训练检查点边界、有限评测及原始数据上传。完整时间和设备分布见FINAL_RESOURCES.json。'%(res['wall_seconds_since_goal_start']/60),'', 'NVML每约30秒采样，实际覆盖%.1f分钟，覆盖期间整机8卡时间加权均值%.2f%%；最近4小时未观测区段按0计的保守插值估计%.2f%%（门槛26%%，目标40%%）。这不是斯卡服务端连续四小时计费/停机判据认证。2026-10-02 18:10（北京时间）服务端通知四小时平均19.9461%%，低于26%%导致杀停；先前43.25%%仅为约109分钟已采样时段均值，不能代表四小时。重连后临时目录消失，8个未完成final按原冻结身份各重试一次；权重、初态、batch及源码未变。没有填充耗作业；GPU任务完成后清理本轮自建监控，保留ToDesk及其他任务。'%(u['covered_seconds']/60,u['observed_time_weighted_whole_machine_mean_pct'],u['last_four_hours_unobserved_assumed_zero_estimate_pct']),'',
 '[科学分支](https://github.com/Jr-kelly/artgym/tree/feat/wuji-width-student-distillation-20261002)；[独立研究Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-width-student-distillation-20261002-final-v2)。v1模型/开发确认/视频、准备Release和旧几何Release保留，新的模型、raw轨迹、配置/采样、实际作业收据、视频/图和服务器SHA独立交付。父权重按旧版本哈希引用，不从头重跑。最短恢复与实际评测命令见REPRODUCE.md。','',
 '唯一优先下一步：先定位并改善严格S2/S5到位精度的保留，使用冻结早期G与主C的失败时序及同incomingRNN执行目标误差作单变量诊断；再选择具体修改。不要先无限延长宽度蒸馏，也不要将长度source3抓姿缺口混入本轮因果比较。']
 (D/'FINAL_REPORT.md').write_text('\n'.join(lines)+'\n')
 (D/'RESULT_SUMMARY.json').write_text(json.dumps(dict(selected_main=freeze['selected_main'],final_freeze_sha256=sha(D/'final-freeze.json'),final_manifest_sha256=sha(D/'FINAL_MANIFEST.json'),primary={r:cell(final,'W120',r,'F',3) for r in ROLES},baseline_F={r:[cell(final,'baseline',r,'F',i) for i in range(4)] for r in ROLES},formal_updates=12800,formal_transitions=13107200,resources=res,second_pair_final_tested=False,second_pair_dev_repeated=True,next='Strict timed endpoint precision preservation before more width distillation'),indent=2)+'\n')
 record('complete_frozen_final_report_written',evidence='research/width-student-distillation-20261002/FINAL_REPORT.md',next='Human inspect final statistics and plots; publish exact evidence, hashes and resource ledger')
if __name__=='__main__':main()
