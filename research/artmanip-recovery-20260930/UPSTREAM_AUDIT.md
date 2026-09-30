# ArtManip → Wuji：源码审计与本轮参考

起始实验 SHA `c1c489f7f76ba068dc1e583da0b4d14b28b1f443`；2026-09-30 06:42 UTC 实查 GitHub 无更新。上游 main `63b94fb3364596db51b7e4651b3c3c98ff994710`。论文 PDF 及文本下载在 `upstream/`，原文 §3.2–3.4、§4.1、§6、C.2–C.6 已读。下表中“参考”是代码实现；生效配置和实测将由 `runs/artmanip-recovery-20260930/reference-precheck/` 及 RL `startup.json`/`learning.jsonl` 补证，不能把尚未运行项当成实测。

|项目|论文|固定上游源码|既有 Wuji|本轮参考与分类|
|---|---|---|---|---|
|任务范围|30实例训练、5留出；类别级多抓姿|`sample_grasps` 随实例随机抓姿池|固定刀，0/1近邻、2为另一旧簇、3新簇|只固定刀0/1/2/3；每reset随机来源及扰动，记录实际访问；主动缩小范围，非类别复现|
|初态|每实例1000候选，一秒静态筛选|保存关节位置/目标、物体两link位姿、接触；reset目标恢复|75维既有抓姿及±.01rad、±.5mm、±.5°扰动|新RL train128/源；BC复用旧1024轨迹；全新dev32/promotion64/final128/源，最终不传计算机；移植必需|
|手与驱动|Sharpa22动作|配置关节索引，PD位置控制|Wuji URDF20仿真关节，thumb索引16:20，digit-filtered碰撞|保留核验过的Wuji顺序、官方MJCF敏感性PD配置，不称实物校准；移植必需|
|目标增量|全手 α=1/40|`ArtManip.pre_physics_step`: previous+speed×sim.dt×action；speed1、dt≈1/120，控制inv4|非拇指init+.04×a，thumb previous+.025×a；clamp目标|直接调用上游全增量路径，实测每输出的有效步长，不把论文.025静默替换进去；整体系统改动|
|裁剪与平滑|动作[-1,1]|RL player/env裁剪；relative不应用moving average|先裁动作，再混合目标、限位，再内部unscale→scale|参考相对分支；M/E保留原混合链路；动作/prev action/目标一致性用旧数据重核验|
|输入与循环|init57、proprio59、goal1、priv21→latent16；LSTM512|SAPG独立actor/critic、各自LSTM、归一化裁剪、contact仅critic；实际coef分组|Wuji policy111、priv21、contact5；历史teacher另有坐标/四元数半球变换|RL用原始资产坐标观测，111/21自适应维度；BC旧变换保留；来源ID不入推理。Wuji维数为移植必需，观测约定差异为系统改动|
|指令与到位|相对+.04/0，到位换向|训练successHoldRange[0,2]秒；20次成功或10秒未完成reset；eval默认hold1.5秒|外部固定2/5秒，20秒完整回合，无到位换向|RL恢复随机到位保持/换向；独立F40秒、10mm容差、固定hold1.5秒；S旧2mm末.3秒不变；主动区分任务|
|奖励|progress1000、target1、linear-50、angular-2、contact1、hand-.001、smooth-1、drop-1、success50|速度用相邻姿态差并限幅；smooth是目标关节差平方；success保持后一次；与文字不同|corrected奖励，低稳定成本-.5/-.02/0、drop-25、dense项旧.1/专家3为1；alive .1|参考恢复上游权重、无alive，保留已存在corrected时序修复，明确偏离上游bug；不是完整逐字论文实现|
|奖励时序疑似错误|进度是旧目标最佳距离改善|上游先 `update_goal` 重置 `mini_goal_distance`，后与切换前 `goal_distance` 比较，可能把新目标距离奖励到旧转移|已存在corrected分支把进度算在换向前|复用已修正分支，单独保存数值反例；明确实现错误，不据此断言旧统一失败根因|
|课程|附录warmup100、持续1000；正文叙述性能动机|默认warmup200、total2000；实现分母total-warmup，在2000结束|旧稳定项起终值相同，课程虽推进权重不变|参考默认上游200→2000，-.5等旧解释不再适用；每epoch记录真实权重，不预先缩短日程|
|动力学/接触|Sharpa有效摩擦2–4、knife damping700–1300，专门标定非真值|随机质量、摩擦、关节阻尼与外力|35g分配、阻尼.3、物体摩擦3、手1、Wuji碰撞；无外力/物理随机化|保留这套静态已验证Wuji profile；不复制Sharpa参数。参考YAML jointNoise=.01，但ArtManip在randomize=false时强制joint_noise=0，实际无观测噪声/外力/物理随机化；这一实际边界不代表硬件有效|
|终止|5cm或1.57rad掉落|实现同阈值，另episode/goal timeout|训练同物理终止，S额外10mm/.25rad评分|参考训练上游；F记录全程漂移/旋转/存活；S严格独立复算。S不通过不写成F失败|
|学习预算|约2B交互、2×5090约48h、SAPG、4 mini epochs|默认horizon16、seq16、block3200、minibatch32000、LR1e-4|horizon32、block512、低LR BC800更新即停止|RL random，LSTM512+encoder256/128/16、5blocks、horizon16，LR2e-4；全20epoch预检测量后锁定≥4段，不用pilot宣判方法无效|
|恢复|未详述|PPO状态可恢复，但PhysX state为空|BC保存Adam/CPU CUDA NumPy RNG|RL额外保存RNG/实际optimizer更新；恢复时明确reset物理/RNN，不宣称逐位不中断；M/E同BC100真实Adam/RNG|

## 本轮预先固定的判断

优先B联合RL；C仅改变专家监督标签：M=raw μ、E=clip(expert μ)，预测端不clip loss。更新预算按新增800/1600/3200/6400检查，可证据触发12800；最低3200前不作平台结论。验证误差、阶段保持、刀身三类信号至少连续3点平台才停，32样本边界变化用64复核。

选择顺序在结果前固定：最差S成功率 → 最差S阶段末保持率 → 最差刀身稳定 → 平均物理目标误差（BC）或平均阶段目标误差（RL） → 较早检查点。固定预算末点单独保留。F不是由S轨迹改标签，独立运行40秒；F至少完整一轮、10mm容差、1.5秒到位保持后换向，报告cycles/生存/最大漂移旋转。S全20秒每阶段末9步2mm、全程有效、10mm/.25rad，四来源两协议>=80%、body>=95%，且相对负责专家降幅≤10/3pp。

## 证据边界

代码/资产、训练拟合、开发闭环、新冻结最终、独立复算、固定初态视频分别存放。旧最终128只作已见历史证据。无未见基础抓姿、形状泛化、自主取刀和真机验证。新参考与混合BC的比较包含接口、奖励、观测及指令多项改变，不能归因于单项。

## 实测补证（2026-09-30 07:02 UTC）

`reference-precheck/report.json`：128环境全通过一秒静态body，来源29/33/28/38；实际step=0.00833333377rad，策略dt=0.0333333351s，映射误差0，物体target变化0。`pilot-throughput.json`：20个完整SAPG epoch=1,638,400交互/720次优化，每epoch实际36次优化（包含SAPG经验复用），平均6.155s，后10轮6.510s。启动/保存额外132.99s。随机初始checkpoint SHA `c4cbd272868da979aa7b34ad560b7d7928fff5d392de9035a43b9dfce468af8d`。这仍是吞吐预检，非收敛结果；F/S独立评估未结束。

原始配置已打印在pilot wrapper output.log，实际构造env配置在startup.json；此前没有单独config.yaml，归档不虚构该文件。后续正式入口直接截获Hydra与learner完整解析配置，并另存实际env配置。源码pin首次因symlink assets使IsaacGym相对路径逃逸而失败；改pin内硬链接assets后已真实训练成功。

### 配方选择补充

参考的初始LR2e-4采用论文Table9及既有Wuji训练配置；上游当前YAML是1e-4。这是预先明确的配方选择，不宣称逐项使用开源默认值；自适应LR随后按实际KL更新，逐epoch已记录。手/刀物理、关闭外力/物理随机化也是已列出的Wuji配置匹配项。

历史 `weights-index.json`43项与 `failure-diagnosis.json`复核：BC100原source3两个S协议均有113/128条“body稳定但严格失败”，支持区分端点误差与掉落；不独立证明动作监督、状态偏移或容量根因。本轮M/E与新F均保持此证据边界。


## 后续保持目标与训练初态修复（2026-09-30）

保持任务`wuji_artmanip_clock_hold`在同一全增量控制/物理配置上增加2/5秒固定时钟、持续2mm目标奖励和绝对刀身位移/旋转惩罚，20秒回合；这是明确改变训练任务的目标组合。原参考仍保留随机到位后换向、原课程和四段预算。

完整512行静态审计发现原训练源0行47/94/104/117在前3步越界，两个任务的零动作轨迹哈希完全相同，不能归因于保持奖励。按预注册映射仅替换这4个训练槽位，新池SHA `d885794f6bd5c77a71591c5d5e17753b4679252c8582587ab7217d6d61c73836`，各来源独立状态数124/128/128/128、采样槽位仍各128。修复池512/512通过20秒原阈值静态检查，目标变化0、时钟/重置通过。两个新增续训臂均从原RL1000真实优化器状态开始，使用同一修复池和各1000epoch。原完整池四段基线单列并注明少量不稳定扰动；评估集不筛选，最终S标准不变。证据与事前选择见`reset-repair-comparison-plan.json`和Release静态诊断归档。


对已有专家序列的目标速率诊断（`expert-target-rate-active-diagnostic.json`）：参考接口最大目标速率0.25rad/s，旧专家源2的2秒协议在首个末端保持采样时刻，其记录目标相对初态所需最短目标移动时间中位数约2.38s；128个有效记录均超过该采样时刻1.733s。这里只比较记录目标轨迹的速率需求，并不证明滑块任务没有其它成功轨迹，不把即时旧权重失败当作新接口无效，也未据此改变参考控制步长。首版未筛除末端已失效回合的诊断保留，active版本为正式解释依据。


旧评估报告的`action_control.support_span_rad/thumb_step_rad`来自通用兼容配置；对reference任务不是实际生效接口。历史reference实际控制以单步实测0.008333rad及任务源码为准，不能误读为.04/.025混合接口。新报告明确区分`full_incremental`的实际步长与mixed接口；仅补正元数据，轨迹和评分未改变。


训练探索日志补查：`exploration-runtime-audit.json` 固定了上游原文件SHA及对应行。实际5个SAPG block的embedding为[50,37.5,25,12.5,0]，intrinsic entropy系数为[.0025,.001875,.00125,.000625,0]，每块1024环境。正式评估固定block0/id50，与固定上游 `eval_consecutive.py`、`infer_teacher_impl.py` 默认一致；未据训练熵差异认定选块错误或另开选块实验。Gaussian熵是训练分布统计，不是裁剪后执行动作熵，也不证明探索对某一来源有效。

学习率字段有时序区别：TensorBoard `info/last_lr` 是最后一次优化更新返回的LR；`learning.jsonl` 的 `lr` 则在该epoch末尾自适应调度完成后读取，可能已经变为下一次更新的LR。归档Adam参数组保存后者。该区别由 `a2c_continuous.py` 返回值及 `a2c_common.py` 调度顺序核实，不是本轮新改学习率。
