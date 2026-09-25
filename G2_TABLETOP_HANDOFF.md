
## Overnight G2 20260926 2026-09-25T18:30:55.627010+00:00

R1-05新获取候选1已完成平放取刀/翻掌/2秒保持，漂移0.454mm/0.003021rad；实际为拇指中指无名指三点接触，食指和小指自由，非四指都接触。当前相对功能姿态81.88度/21.716mm，角度改善但中心偏差更大，操作能力未验证。旧路线无名指底部目标与拇指凸包相交已用LP确证，禁止执行该目标；R1-06只运行无名指卸载保持。正筛查新获取空闲食指/小指的底部支撑。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:27:07.526168+00:00

R1-06启动：R1-04左底中指支撑后仅无名指退出4mm并保持1秒，检查剩余支撑并获取真实卸载末态用于规划。完整无名指深避让目标在joint2/3限位，浅路径虽端点误差0.889mm但关节直线扫掠不满足1mm几何间隙，均已拒绝物理。下一步用实际无触末态做碰撞感知关节路径，不能只重复端点插值。R1-05新四指获取正在抬刀，尚未验证翻掌。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:24:24.419005+00:00

R1-04通过真正的中指避让迁移：先无触移位，再在左底面x=-3.459mm/z=14.167mm建立接触，接触为中指link4而非指腹；末保持4.339mm/0.13029rad。去拇指LP仍不成立，计划再补底部支撑。R1-05启动新获取候选1：四指侧夹、小指避让，名义相对角95.735→78.606度，掌朝向符合任务；普通端点IK有分支跳变，独立启用连续笛卡尔接近/抬起，纯运动学速度0.515rad/s以下、首指令<9e-6rad、臂掌无桌碰。G2伺服/物性不变，明确不同获取控制条件，不作单因素因果结论。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:16:13.488819+00:00

R1-04启动：中指先前移到刀身z=14mm并向下退出，随后在>5.6mm几何间隙下横移到x=-4mm，再建立底部支撑；全指横移扫掠满足4.1mm间隙，端点误差<1um。z=1mm的原下移目标限位不可达；新纵向位置是有界替代，不改物性。仍只动中指，其他电机固定，先保持不放拇指。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:14:51.119038+00:00

R1-02a完整通过中指两段移动及保持，但实际中指接触仍x=+5.675mm，未形成居中支撑；电机目标与实测有0.067rad差距。R1-03扩大退出路径后拇指真正离触，首次离触34.633335s也正是首次旋转失稳，随后刀掉出；只维持12帧无触，G1失败。证据支持原支撑缺少去拇指承载，而非拇指始终无法运动。中指深间隙路线上关节3限位，预筛失败未启动；现在筛查其他IK分支和已无接触食指的左侧底部支撑。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:12:21.620712+00:00

GitHub正常Git推送已恢复：普通工作树push的子进程读.git/config失败；使用本地独立bare发布仓库正常push成功，未改权限、安全、审批或凭据。远端新分支已建立a3afde1。R1-02中指第一次内移运动通过3.016mm/0.07638rad，仍等待完整保持及第二段。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:08:40.638079+00:00

R1-03启动：保留D04原支撑，同材料点退出方向，仅将拇指退出距离4mm改12mm。固定物体几何扫掠间隙单调增加至11.48mm，实际要求整个拇指零接触且间隙>4.1mm保持1秒；与R1-02支撑迁移独立。两项本轮仿真，旧训练保留。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:06:55.926006+00:00

R1-02a启动：D04真实前缀后仅中指在底面依次向x=0/-3mm滑动并各保持1秒，腕及其他指命令固定。全指扫掠几何为有意接触迁移，最大保守重叠指示1.27mm，不能解读为实测穿透或稳定证明。此前R1-02仅环境准备失败，无物理启动，已留记录。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:01:29.307878+00:00

R1-01失败于无名指从角部移到内部的运动阶段：39.6667s首次转角超0.25rad，最大0.25805rad/5.54mm；未到新支撑保持。现有路径只约束端点接触几何，1mm底面间隙小于4mm成对contact offset，需检查完整关节插值的扫掠体；下一对照只改无名指避让路径，保持接触终点与其余指命令不变。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T17:57:05.426736+00:00

R1-01启动：沿用D04中指迁移，改无名指底面x由+9mm到-3mm，z=-12mm；先建立支撑保持，不立即放拇指。真实D07无名指法向主要侧向，食指离触；简化静力LP移除拇指在mu0.5..3均无解（平均接触点模型，不是不可行证明）。新试验记录整个拇指几何间隙、实际接触及同步近景，主物性不变。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T17:54:13.448279+00:00

新过夜Goal启动：本地与GitHub均为7dea82e，干净工作树切独立分支；01:52:35至09:52:35北京时间，09:07:35开发截止。旧训练88339实查活跃，4090显存8.9/24.6GB，磁盘充足。先检查D07/D10/D11真实接触、整个拇指间隙与去拇指支撑可行性。新预算48次分3轮，当前0次；允许学习但门槛尚未满足。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## G2 分指换握 2026-09-25T17:02:15.151253+00:00

已发布并回下载核验：https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-finger-gait-20260926-v1，15个附件（10段完整无字视频、22.13MB增量证据及报告/校验）大小SHA和下载字节全部一致。代码/运行基准提交3e6486acef0a9a107595a490200cc40f7460c3a8，分支feat/g2-wuji-finger-gait-20260926；恢复D09精确源码3887项SHA通过，生成命令bash语法通过，未新增物理。报告research/g2-finger-gait-results-20260926.md。取刀/翻掌/双指底部支撑成立；拇指释放和整段teacher失败，student未运行。停止扩展并保留11次启动全部证据；下一优先检查去除拇指后的实际接触支撑可行性，再定义单次支撑预载对照。无本轮在途进程，旧训练88339实查仍活跃。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动11/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:57:12.248121+00:00

本轮物理已结束：11次启动、10次物理、9条连续B前690帧均与V2逐元素一致；全部11份源码pin共3878至3887项逐文件校验通过。最远D07取刀/翻掌/中指无名指底部换位保持；D09 teacher0.633s失稳、1.133s全失联、1.6s落桌，600帧离线接口回放误差0。D10/D11不同支撑未完成拇指离触，按停止规则收敛。先读research/g2-finger-gait-results-20260926.md；完整命令在research/g2-finger-gait-20260926.md。正在发布独立分支feat/g2-wuji-finger-gait-20260926及Release g2-wuji-finger-gait-20260926-v1；旧训练88339保留，C/新位置验证未运行。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动11/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:54:14.300531+00:00

D11 ended: middle+ring bottom support retained through prefix, but thumb unload first violates0.25rad at44.966669s, max0.27502rad/5.4165mm; abort before unloaded hold, no policy. D10 and D11 are two physically distinct support arrangements that fail the same minimal thumb-release objective; stop expansion per user rule, not budget exhaustion. Total11 launches=10 physical+1 preflight. Teacher D09 failed, C and new placements not run. Preserve all failures. Next priority is a bounded support-force feasibility/preload discriminator before another release attempt, not RL/retraining.

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动11/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:48:47.497721+00:00

D09 completed continuous teacher trial: pickup/flip/middle migration/hold pass, teacher operates600frames but drops knife; C gated, not launched. D10 actual-contact-anchor unload still retains thumb contact100%, pinky absent; corrected anchor alone did not solve release, stable but requested action failed. D11 tests physically different support (middle+ring both bottom), same4mm material-point thumb unload and1s full absence gate. If the same minimal action fails without new discriminating evidence, stop expansion rather than consume18 by tuning.

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动11/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:43:15.970220+00:00

D07 ring-bottom complete and stable: final hold5.378mm/0.1184rad, actual ring/middle/thumb/pinky contacts; index intermittently absent. D08 retained knife but FAILED requested thumb release: thumb contact100%, pinky0%; do not call unload successful. Actual thumb pad contact y=-1.15mm differed from mesh extreme y=-4.32mm. D10 isolates planning anchor: same D04 support, same4mm/1s, actual material contact point; new full-second no-contact gate. D09 tests frozen teacher from independently validated D04 held endpoint without arbitrary cache regrasp. 10/18 launches.

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动10/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:35:39.634903+00:00

D08 starting independent support contrast from verified D04: only thumb unload4mm and hold1s, middle already on bottom, ring/pinky original side support. Determines whether ring migration is actually needed to free thumb. Two local physics jobs within available VRAM; old training preserved.

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动8/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:35:10.845041+00:00

D07 starting: same successful D06 prefix, move ring via outside corner to reachable bottom z=-12mm. Twenty-point geometric screen found original z=-22.3mm at joint limit, z=-12mm feasible with residual<0.1um. Only ring motor changes; fixed wrist/other digits and original physics. Geometry does not prove stability.

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动7/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:34:11.066319+00:00

D06 finished: middle-bottom then ring unload held 1s, max fixed-world 5.382mm/0.12752rad; ring contact zero, thumb/middle/pinky remain. Budget 6/18 launches (5 physical). Original training88339 verified active; no gait processes remain. Next geometric ring-bottom reachable-point screen; preserve all pins.

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动6/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:32:03.566509+00:00

D05第5度失败中止：固定世界平移4.276mm、旋转0.30298rad，前4度未超门禁；不扩大腕转角。D06仅卸载无名指在途；下一优先单指迁移，不加反馈增益。D05接触字段已核对camelCase localPos0/1并采集。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动6/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:30:55.033265+00:00

D05正在逐度接触保持腕运动；第1度仍通过固定阈值。无名指底部迁移几何残差2.27mm，未做物理；D06只做中指已建立支撑后的无名指卸载+1秒保持，用于验证新的四指支撑组合，尚未迁移或转腕。18上限已由launcher按保守启动数强制执行。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动6/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:26:45.666437+00:00

D04终态通过。5度接触保持的固定腕平移插值在4度时中指不可达(1.57mm)，几何排除；允许腕部有界<=10mm平移后5度各指固定接触残差<0.00003mm，D05启动物理。此处只改规划腕路径，不改物性/动力学。D04日志未提供local_pos字段，接触位置仍是网格估计；新代码记录实际dtype并兼容camelCase，不能误报为已有实测接触点。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动5/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:24:47.704231+00:00

D04单中指迁移刀背边缘并保持1秒通过，最大固定世界漂移2.962mm/.07431rad。其余指电机目标不变；真实接触数据local_pos0/1开始记录。准备5度接触保持腕运动，逐度补偿指基座运动，接触目标不迁移。D03 A已通过，暂不增加其他目标A。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动4/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:22:17.196221+00:00

D03独立A当前腕姿20秒通过2mm/两轮/稳定：四端点0.563/0/0.252/0mm，世界7.122mm/.13993rad。不需要默认搬运；只证明终点手物关系有效。当前原侧夹固定腕刀关系下拇指到滑块多初值IK仍残差32.07mm，新近端点不可行。D04中指底部迁移在途。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动4/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:21:00.714980+00:00

D02中指卸载4mm并保持1秒通过：世界1.582mm/.02124rad；中指保持期接触0，其他四指全程接触且电机目标未变。D04开始单中指绕角建立底部支撑，原前缀与卸载复用。D01仅IK预检失败未simulate；同腕实际q用作求解种子的D03 A已进入物理，不更改限位。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动4/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:18:06.764223+00:00

核对本机/远端277efe4一致，独立分支已建立。相对旋转103.6009度核算成立但非因果；保留抓姿0/1旧操作证据。D01 A当前腕姿、D02中指卸载各独立源码已启动，分别PID928290/933348。原训练88339实查活跃。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动2/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## 2026-09-25T15:21:44.180461+00:00 取刀翻掌证据已发布核验

https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-sliderdown-air-flip-20260925-v1：9个附件大小/SHA全部验证，4项源码与轨迹（含两次失败）、四段无字视频、完整命令/报告；增量归档4.98MB，16项关键归档内容与本机源文件一致。源码分支feat/g2-wuji-air-flip-20260925已同步，Git HTTPS helper反复无法读取.git/config，改用GitHub Git对象API，校验树完全相同并已对齐本地分支。下一会话先读research/g2-air-flip-results-20260925.md；取刀翻掌通过、手内调整失败、无新策略操作这三点不变。没有在途本轮任务；保留原训练88339。

## 2026-09-25T15:18:20.908356+00:00 修正路线当前收尾

先读research/g2-air-flip-results-20260925.md。用户滑块朝下→取刀→小臂手整体180°翻掌已验证V2；后续V4开环和V5腕真值跟随均在手内调整失败，无新teacher/student操作。V5第704帧因52.1mm刀身偏移中止；4个物理进程已结束。下一项仅建议固定翻掌前缀、分指迁移的有界方案，未执行；无新训练，原88339保留。旧端立不再符合用户现实路线。即将新增Release只备份本轮4项和诊断；旧v6/v7不覆盖。

## 2026-09-25T15:15:42.797914+00:00 空中换握第一物理对照失败

V4前690帧与滑块朝下V2取刀/翻掌逐元素一致，后续12秒换握期间渐进转偏：第8秒0.329rad，第10秒0.663rad，第11.96秒1.317rad/28.5mm，滑块被动打开；在转运初段落桌，operation_steps=0。不要归因唯一为末段减压：减压之前已经转偏。完整42秒失败保留。

V5仅改 --seat-feedback object-truth，手指/物性/源码pin与V4相同（清单SHA5d1c7232…），使用既有5mm/0.05rad限速IK及50mm/0.8rad刀身范围；仍是理想定位对照。PID556357，结果待收。代码已推GitHub d4b68d8；origin是本机备份仓库，外部推送需从/home/agiuser/artgym-full-backup-20260925-v1/code-branch完成，主工作树HTTPS helper读取.git/config报权限错误，已用备份中转推送成功。

## 2026-09-25T15:08:45.606731+00:00 滑块朝下取刀翻掌通过；手内调整在途

B-sliderdown-pronate180-h30-v2完成25秒，750帧，无操作：滑块面朝上分量-0.9993→+0.9850，掌心-0.8043→+0.8044，实际翻179.821°；翻转期间刀手相对最大平移3.941mm、转角0.1556rad，无失联或落桌。完整末秒保持通过。手/刀物性同v1字节一致，臂关节位置与指令/实测速度无超限。预览http://127.0.0.1:8767/g2-sliderdown-pickup-flip180-v2.mp4。

从v2实际flip末态推导手内规划，不用它重设状态。单求解路径v3接触误差15.47mm被几何筛除，未做物理。v4加入功能角度种子比较，接触误差0.149mm、臂位置残差0.60微米；实际12秒换握正在B-sliderdown-airseat-teacher-v4 PID530855中验证。任何成功需读report/trace，不把几何路径当物理。原88339保留、无新训练。

## 2026-09-25T15:04:52.018916+00:00 用户补充初始滑块面朝下

当前正确路线：初始滑块朝下、掌心朝下侧夹→小臂与手整体翻180°→滑块和掌心朝上→手内调整→冻结伸缩。上一个v1滑块初始朝上仅为翻掌控制对照：750帧/25秒，179.818°，相对位移0.657mm，未掉刀；不代表修正路线完成。新v2从滑块朝下正常摆放开始，考虑3mm突出滑块，初始刀心0.7571m后自由静置2秒，再一次仿真定位规划抓取。没有改变刀/桌物性、没有夹具或端立。B-sliderdown-pronate180-h30-v2 PID508742启动，结果待核。

## 空中翻掌新路线 2026-09-25T14:59:32.827724+00:00

用户否定端立换握的现实适用性。当前分支 feat/g2-wuji-air-flip-20260925，运行目录 runs/g2-air-flip-v1；先读 research/g2-air-flip-20260925.md。改为掌心朝下取刀→空中约180°翻掌→手内调整→冻结策略。旧v6/v7保留，不再代表新路线成功。先验证夹持翻掌，无新训练；原88339保留。
# G2＋Wuji 桌面取刀→伸缩（2026-09-25）

分支 feat/g2-wuji-tabletop-20260925；工程 /data/research/artgym-g2-tabletop-20260925；实验 runs/g2-tabletop-v1。本轮仿真基线及20次初步验证已交付：固定A63/B65/C66两轮10mm/稳定通过，B/C未全过2mm；C是仿真定位及理想初始化。小变化各组初抬10/10、到接管0/10、整段0/10，9次转腕掉刀+1次端立倾斜超限，条件操作未评估。成功/失败视频和原始证据已发布核验v6/v7。无新训练，原训练保留。

任务：固定刀具、固定正常桌面摆放、一个功能抓姿；G2右臂接近/闭合/抬起/移到操作姿态；同一仿真连续状态接冻结teacher再student。模型源 /data/research/ArtBot/G2_crsB_wuji/robot.usd，禁止套用Franka安装或参数。

A预置→teacher；B实际抓取→teacher；C实际抓取→student。先A定位场景/接口，再B定位抓取末态/接管，最后C初始化/历史。无瞬移/缓存重置/物体约束/隐藏外力/驱动滑块。20秒操作，每5秒按外部时钟换向。保留原手/刀物性和冻结权重，新增机械臂驱动与碰撞单独审计。

接管记录测量q、实际命令target、固定物体/手初始参考、清零RNN；历史仅来自执行数据，可用停稳积累50帧。student物体初始位姿若读真值标记理想初始化对照，不宣称可部署。

固定场景接通后先冻结代码/参数/抓姿，再确定seed和20个小范围位置/朝向偏移；全量保存失败。分报抓取、条件伸缩、整段成功；10mm端点末0.3秒、2mm诊断、刀身10mm/0.25rad稳定与掉落分列，参考固定在接管时。

交付新分支/新Release、运行命令、完整无文字视频/失败视频、轨迹和分类，不覆盖旧结果或历史备份。原4090训练88339保留，运行前重查显存；仅进行有用仿真，不为占用GPU启动无效计算。

当前续接状态：20次已全部结束并原始审计、v7上传及8附件/归档核验完成，不重启旧driver或重跑这些失败以替换统计。先读research/g2-tabletop-final-report.md及delivery-audit.md。当前瓶颈是获取转腕/放端，泛化未解决；建议下一轮只比较5秒与10秒转腕的6次有界对照（原位置+两个已观察失败位置），未执行。若继续，应新建实验记录，保留冻结v6/v7；不要自动扩大RL或重训teacher。原训练88339保留。

## 17:13 CST 进度

整机88链接/87关节已导出；右臂7+右手20活动关节，其他固定。安装偏移34.1mm/Rz(-90°)，无Franka参数。原手URDF哈希保留。几何审计table_grasp_geometry.json：3抓姿slider朝上穿桌40–44mm，朝下更差；直达功能抓姿不可无碰撞取得。A-source-gains-v1已完成但失败：8mm行程、右臂和刀身漂移；原增益100/1、重力开启。A-servo-v2正测试1000/20；A-gravity-diagnostic-v2关重力仅定位，不当正式方案。interface-v2证明初始观测与原环境最大差1.2e-7、动作8.94e-8；student init必须使用raw _get_init_obs（actor prefix另做frame/hemisphere转换），已修正在新代码。所有新试验由launch_g2_trial复制独立source-pins运行。

## 17:21 CST 初始化问题定位及A恢复

A-original-fixed5-v1在原环境20秒所有端点2mm/稳定均成功。A-initialization-handonly-v4仅将episode初始化移到prepare_sim之后、首次simulate之前，并首帧按原at_reset_ids语义组观测：10秒39.5mm行程，端点2mm/全程稳定通过。此前A1–A3失败不能作为改物性必要性的证据；均保留为初始化错误对照。G2 V4操作姿态改world yaw90以远离第7关节限位，保持腕部重力方向不变。A-g2-initialized-v4（手/刀原物性、右臂1000/20）、A-g2-source-gains-v4（右臂100/1）正在20秒操作，均已一轮成功。B-direct-grasp0-v5开始真实正常桌面抓取，首次控制前初始化为开手+平放闭刀，此后禁止状态写入；实际抓取失败将跳过策略接管，不伪造C结果。命令参考各-process.json，源码pin独立。

## 17:32 CST 续接与结果汇总（时间纠正）

A-g2-initialized-v4成功：20秒四端点全部2mm内，40.019mm行程，世界漂移8.450mm，手内4.855mm。有效原G2驱动100/1对照A-g2-source-gains-v4也全部端点成功，但世界漂移79.714mm，因此新场景暂用右臂1000/20（仅仿真伺服调整，未硬件标定）；手刀参数不变。
B直接抓姿0、侧滚yaw180的抓姿0/2高度+15mm和0mm共5次真实抓取均未抬刀，操作跳过。两个yaw0侧滚候选IK失败单列，不计物理成功率。详细目录B-direct-grasp0-v5、B-rolled-yaw180-grasp{0,2}-v7、B-rolled-contact-grasp{0,2}-v8。功能抓姿支撑指需进入桌面下40–44mm；侧滚−75度仍有14mm穿桌，抬高则错失接触。下一步有限尝试侧向上缘夹持，再真实抬起/就位，禁止隐藏重置。
student-interface-v8：50实际执行历史帧，输入最大误差1.19e-7、动作2.32e-6，改变实时物体真值不影响student输入。仅接口验证，未完成C实际抓取。无新训练、无20次扰动验收。原训练88339仍运行。

## 17:45 CST 接触几何诊断

新增plan_g2_edge_grasp.py，用所有手碰撞凸包顶点检查桌面约束，先求侧边触碰，再求开指/闭指电机目标。v9只约束最近顶点，实际主要压在上表面；B-edge-{direct-,}grasp0-v9均失败。v10加入有限关节积分伺服（gain1/s、限幅0.08rad，只调整驱动target，不施加外力），闭合接触仍未形成抬刀。所有实验独立source pin、旧失败保留。
法向侧夹v11要求指端支持面位于刀身两侧，几何桌面净空0.63mm；真实v11仍未抬起，怀疑闭合目标仅约0.8mm预压不足。v12允许4mm电机目标过行程（实际指头由接触阻挡），正在物理验证。同时A-g2-integral-v12确认新伺服不破坏冻结teacher。普通姿态roll0法向侧夹候选thumb误差21.7mm，几何不合格，不启动该物理试验。
DOF传感器接口返回False，当前TacSL IsaacGym不支持该actor的关节力测量；v10/v11力数组无效，不当实测。v12起以NaN明确不可用。轨迹审计证明G2腕部FK与仿真一致约1微米/2.4e-6rad，已完成路径关节限位及命令速度无超限。碰撞计数从get_env_rigid_contacts记录手指-桌面/刀具配对。

## 17:54 CST 抓取子阶段首次通过

B-pinch8-transport-grasp0-v14从正常桌面连续抓起，完成20cm抬升、搬运及停稳，grasp_success=True。只改变手指闭合目标预压4→8mm，未改手部增益/摩擦/物性；该8mm是求解电机目标时的虚拟过行程，实际手指由接触阻挡，绝非写入刀具/手的物理状态。原4mm版本能抬升但搬运时长轴下倾后滑落；v14夹持通过，尚未操作。B-pinch8-teacher-grasp0-v15正在跑冻结teacher完整接管对照。
A-g2-integral-v12新伺服复测：40.090mm行程、四端点2mm均过、世界漂移7.744mm、旋转0.1498rad，全程稳定通过。
简单手指插值就位B-normal-seat-grasp0-v13抬升后掉落，视频/轨迹保留。尝试保持刀具长轴近水平的B-pinch4-level-grasp0-v14在抬升后规划发生IK解分支跳跃，被连续性门禁中止，保存partial-trace；这是搬运规划失败，不是物理抓取失败。暂不扩大该路线。
plan_g2_seating.py生成接触保持的腕部+手指路径：固定腕部插值v15中间接触误差达15.5mm；加有界腕部位置调整v16全部接触几何误差<0.1mm。B-contact-seat-grasp0-v16正在真实自由物体仿真，先抓取再8秒就位；没有物体约束、位姿写入或滑块驱动，几何可行不等于物理成功。
仍未训练、未做C真实操作或20扰动验收，未发布GitHub。下一步收v15/v16结果定位策略接管与手内就位；不要把首次抓取成功写成完整任务成功。

## 18:12 CST 连续IK/就位反馈与发布进展

代码和资产已首次推送GitHub feat/g2-wuji-tabletop-20260925，提交4e740cb，报告research/g2-tabletop-baseline-20260925.md。Release尚未创建；package_g2_evidence.py已实现仅新增证据归档，历史源码用base1482edd+按SHA去重的覆盖文件恢复，不重复上传历史或冻结权重。
B-pinch8-teacher-grasp0-v15完成：抓取到接管成功1/1，但接管后掉刀，0完整循环，四端点仅伸出端碰巧满足10mm（掉到桌上滑块停在伸出位置），不能当成功。接管相对原功能抓姿位置差8.5mm、旋转约91.7°。C-pinch8-student-ideal-grasp0-v21（PID3288961）正在同一抓取后跑student理想初始化对照，不能先宣称完成。
B-yaw90-contact-seat-grasp0-v17连续IK已可达，但就位中段掉落。反馈v18/v19分别在第一帧和早期触及腕关节限位，被门禁中止，failure.json/partial-trace保留。改用关节7冗余姿态-0.7rad、刀具正常桌面x=.45,y=-.3,yaw180（仍离桌边150mm）后，完整就位路径关节余量至少0.258rad。v20初始IK分支种子不一致导致预检失败，v21修复初始姿态求解备用种子；不得把预检失败当作一次物理抓取失败。
B-posture-openloop-grasp0-v21（PID3287326）已抬升，随后就位仍掉落；B-posture-feedback-grasp0-v21在就位0.3s因1.08mm瞬时限速IK残差而中止，尚无掉落证据。v22（PID3294602）保留关节限速，跟踪容差改5mm/0.05rad，并从上次关节目标限制每步变化；这是有界反馈控制允许短暂跟踪误差，不是更改任务的成功阈值。
新增record_g2_status.py可核对真实本机进程/补记所有结束事件，current-status.json为快照。原训练88339保留。下一步收C、v22；检验反馈就位是否物理可行，再考虑接管。没有新训练、没有20扰动验收；目标仍active，不能仅以发布基线标记完成。

## 18:17 CST 首轮A/B/C收齐，接触力矩假设

C-pinch8-student-ideal-grasp0-v21完成：抓取1/1、条件伸缩0/1、全段0/1，行程7.543mm，0循环，接管后掉落。student SHA022ad8c7b3af18e25681fcd4073c1b48858621470293036df0311c488068e0f5。B/C前600帧q、arm_q、object、wrist、slider、targets逐元素完全相同，证据bc-acquisition-prefix-parity.json。A仍成功，B/C均失败，不代表唯一原因已锁定。
V22反馈在就位0.53s跟随刀身转动造成38.7mm/0.260rad残差，限速门禁中止。不能继续仅放松容差；完整反馈轨迹保存。开环v21在就位3.7s、进度约46%时突然翻转掉刀，之前刀身位移约3mm、旋转约5°，各指仍接触。几何路径将法向线性转到约40°，但刀身对角棱边径向约23°，可能产生轴向翻转力矩。
plan_g2_seating新增normal-path=radial，只改变接触方向路径以接近穿过刀身中心的夹持方向。生成contact-seating-radial.json（全程几何残差<0.22mm）。B-radial-seat-grasp0-v23正在运行，默认不使用动态物体反馈；x=.45,yaw180,arm joint7=-.7，其余物性/冻结权重不变。新增假设尚未物理验证。Release准备发布首轮失败基线及完整证据，不意味着goal完成。

## 18:26 CST 首轮Release已核验，当前在途

已发布 https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-tabletop-baseline-20260925-v1 （prerelease，不覆盖旧Latest）。8附件大小与GitHub SHA256全部通过，验证文件runs/g2-tabletop-v1/release-baseline-v1/publication-verified.json。包括38项已结束记录、A/B/C完整视频及代表性失败；增量证据23.7MB。B/C源码分别恢复3850/3854文件并全部hash相符。分支已推82e6743。
V23径向法向路径仍就位掉落，比线性版本更早（物体高度<.85发生16.37s，对照16.93s），因此不支持“仅改法向就能解决”假设。不要把此前力矩解释写成已确定唯一根因。
正在运行B-hold-pressure-seat-grasp0-v24（PID3360663）：相同90度侧夹/线性接触路径，将8mm电机目标预压保持到就位80%，最后20%平滑回到原功能目标。旧路径过早线性降到4mm附近时掉落，故测试压力时序，未改物性或增益。
B-halfroll-pinch-grasp0-v24为半侧滚抓姿（roll-45几何）首次IK预检失败，未做物理；B-halfroll-free-arm-grasp0-v25（PID3365236）取消不适合该姿态的joint7固定目标，纯自由IK已预检可达，正在实际抓取/搬运。配套seating-halfroll-hold-v25.json由CPU规划中（exec session13433），不是物理成功。
目前本地未提交变更：plan_g2_seating.py新增squeeze-schedule=hold及本手册。新结果尚未进入首轮Release；下一轮增量包只收新增，不重复上传全历史。目标仍未完成、没有新训练、没有20扰动验证。原训练88339仍保留，GPU持续有用负载。

## 18:43 CST 就位路径新增诊断

v24保持8mm压力到80%仍掉落；v25半侧滚-45抓取/搬运成功，但手臂关节插值有大绕行（joint1变化约4.47rad），不能当最终可接受方案。v26半侧滚换握仍掉落。v27整指分批路径几何误差约20mm，未进入物理。v28小步交替路径几何<1mm，B-wave-seat-grasp0-v30已执行到换握中段，仍发生掉刀，最终报告待收。

B-preoriented-seat-grasp0-v29先把已夹刀转到训练物体朝向再换握，仍掉落，不能归因仅为重力。A-flat-gravity-handonly-v29在同样平躺刀具朝向的预置功能抓姿下10s握持稳定（4.54mm漂移）但回收误差16.14mm，说明重力影响操作但不是换握掉落的充分解释。

新增plan_g2_static_seating.py对已有几何路径做有界逆静力诊断：规划五指接触力满足重力/合力矩与mu1摩擦锥，再用J^T f/Kp转换为电机位置目标；所有物性不变，不把规划力直接施加到手或刀。质心暂近似刀具根坐标，预压拇指1.2N；最大理论关节目标偏移0.129rad。B-static-seat-grasp0-v31已启动，12s换握，需真实物理验证。原训练88339继续，未训练新策略、未20扰动验收。

## 18:49 CST 接触反馈诊断与握持判据

v31逆静力开环仍掉落。v32平移真值反馈在第544控制帧因位置偏离63mm中止，刀身旋转仅0.17rad；简单跟随平移不能消除负载下的持续下沉，禁止只放宽门禁。v33手指接触IK反馈第406帧拇指残差10.3mm中止；查明柔和支持点的导数遗漏了顶点权重变化项。v34修正完整支持点Jacobian，中心差分误差5.14e-11；受力映射仍使用瞬时接触点刚体Jacobian，不能混用两者。B-finger-jacobian-feedback-grasp0-v34正在运行，仍是仿真真值定位对照。

新增g2_tabletop_metrics.acquisition_hold：接管前最后30实际停稳帧/1秒，刀身高于0.85m、手内位置在参考50mm内、相对漂移10mm/0.25rad内、至少90%帧拇指与≥2支持指接触；新运行同时记录刀桌/臂手桌面接触数。功能抓姿旋转差单列，不能掺入抓取成功率隐藏失败。原B/C回查通过，手内停稳漂移0.0049mm，功能姿态仍差91.67°，因此原抓取成功结论不变；旧轨迹未记录刀桌接触时标null。

所有新路径/反馈仅输出有限驱动目标，无直接物体施力或状态重设。没有新训练、未接通B/C、没有20扰动验收。准备以82e6743为base做下一份增量证据，新release不得覆盖第一版。

## 18:51 CST 初始换握参考核查

v34修正Jacobian后仍因拇指接触目标不可达而在换握早期中止，因此v33失败不能仅归于导数漏项。实际抬升末态相比几何侧夹 wrist-in-knife 旋转约8.3°、平移范数约21mm（腕部离刀较远，转角放大平移）；拇指支持点已经在刀身上棱附近，原就位计划却仍从理论侧面接触出发。

新增actual-pinch-lift-v35.json从v31真实抬升末态测量q、腕刀关系及接触法向生成，仅作为换握规划起点，不用于初始化/重设仿真；真正桌面抓取仍沿用原edge-pinch8。plan_g2_seating现允许记录起始法向并逐步过渡。seating-from-actual-v35正在CPU规划，需完成几何门禁后验证真实连续物理。当前无试验成功换握，A/B/C结论不变。

## 18:56 CST 实测起点结果与有界姿态伺服

v35实测起点开环仍掉落。v36实测起点+逆静力/手指真值反馈能把早期接触IK残差降到数值零，但换握1.07秒刀身绕自身长轴翻转约0.81rad后拇指失去可达接触，12mm门禁中止。故初始误差和求解精度均不足以解释/消除动态失稳。

v37在同一v36基础上增加刀身位置/姿态反馈；仅经已有手指电机目标，绝不直接向刀施力。规划恢复合力上限0.25N、合力矩0.008Nm，刚度20N/m和0.04Nm/rad，阻尼0.3Ns/m与0.001Nms/rad，约束接触法向0.04–2.5N和mu1摩擦锥。这些是控制规划变量，非实测力或外力接口。代数审计通过（2mm参考扰动→0.04N规划纠偏，力矩/合力残差<1e-6），真实物理正在B-object-servo-seat-grasp0-v37（PID3507516）验证。

GitHub分支已推e8b0f3d；其后object-servo和操作失败分类仍未提交。下一增量Release待收v37后一起封装，base82e6743、排除首包MANIFEST已含试验。没有接通完整B/C，没有新训练或20扰动验证。

## 19:03 CST 空中伺服结果与桌面支撑路径

v37完整物体姿态伺服仍在1.3秒左右翻转/接触不可达中止。v38保留原几何夹持电机目标，仅增加姿态纠偏残差，仍超50mm/0.8rad门禁中止。已保存所有源pin、轨迹及无字视频；没有扩大控制界限或改物性。新失败分类区分operation_drop、endpoint_error、unstable_drift；循环计数需该完整循环保持握持，不能把掉桌后的端点巧合计为循环。

进入有物理区别的新路径v39：闭刀从原正常桌面平放开始→侧夹抬起→机械臂将刀转为竖直→把建模+z平端放回同一桌面→有桌面端面支撑时换握→重新抬起→操作。不是预先竖放，不是夹具/桌边条件；全程仍只写电机目标。平端为当前简化刀具模型定义，需实物端部几何核验，不能称已可部署。刀具端面支持必须在实际接触数据中连续最后1秒≥80%帧成立；手指桌碰撞则中止。

几何审计：原3功能抓姿平放穿桌约39.9–44.1mm；模型+z端着桌且长轴竖直时，3抓姿手网格净空14.0–17.3mm。G2连续IK候选yaw250/270位置残差<12微米，但经过arm joint6限位，不宣称有充足裕量；选择250的相邻关节变化较小。B-table-supported-seat-grasp0-v39 PID3539702正在真实验证，尚无支撑/换握成功结论。

代码分支e8b0f3d之后的伺服/桌面支撑及汇总将在新提交推送。collect_g2_baseline_results.py 固定A-v12/B-v15/C-v21，明确各组仅1个开发案例，其他变参数实验不混成成功率。下一份增量包排除第一份已含试验；仍不重复旧checkpoint和全量备份。

## 19:16 CST 第二份发布已核验，竖刀松手与接管诊断

Release https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-tabletop-seating-20260925-v2 已发布，6个附件大小/SHA256全部核验。增量包12.4MB、16项新增已结束试验/诊断，排除首包内容，v36源码恢复3862文件一致。local release-seating-delta-v2/publication-verified.json。初次用短提交号target遭GitHub422，改完整cd895e6e8c5a56291b55ebe7132a6810b56d6166成功。

v39端面支撑确实建立：最后1秒刀桌接触100%、手指桌接触0，但滑动换握时仍把刀推倒。过程中滑块因重力被动全开，非学习策略或直接滑块驱动。v40新启动时审查发现transport会错误恢复侧夹目标，立即SIGINT，部分轨迹/视频保存并标CodeReviewAbort，不当物理失败；新v41修复。

v41立刀后改松手撤离→功能开手重新接近，但刀在松手阶段已由3.53°倾斜扩大至7.93°，撤离时倒下。v43增加四次1秒的有界腕部找正（25mm位置边界、结束倾斜<0.02rad），卸载夹力后再从实测接触向外求开手目标；PID3598484正在执行。这里增加了仿真真值定位，不能当可部署感知。

A-open-slider-takeover-v42用真实一致的打开滑块初始观测，冻结teacher握持未掉，但10s回收误差42.09mm、行程11.18mm、0循环。说明被动打开本身可能妨碍接管，不能只改手内刀身姿势。正在测试A-grasp1-axis-shift4mm-v44（PID3605463）：闭刀抓姿1、刀沿自身轴-4mm相对手的预置诊断，以验证另一端着桌时所需小净空偏移。另一端着桌能让重力保持闭刀；functional-open-negative-grasp1-v44.json正在配套几何/IK预检，尚未发真实B试验。

当前未提交：plan_g2_functional_open.py、table-regrasp/stand-level/measured-release及A偏移参数、launcher输入pin。已有原A/B/C结果不变，未训练、未20扰动。下一步收v43、v44及negative-end-ik-v44.json，再决定闭刀的桌面支撑路径。

## 19:21 CST 找正预检原因、保闭刀路线与显式80cm桌面对照

v43并未执行找正：目标同时恢复了名义yaw，实际持刀已绕长轴转约12.7°，所以首步腕部修正即超25mm门禁。此前把它描述为实际找正失稳不成立。v46只最小旋转刀具长轴使其竖直、保留实际yaw，配合实测卸压/开手；B-tilt-only-measured-regrasp0-v46（PID3621594）正在75cm桌面，只评估重抓到操作位，不调用策略（滑块已被动打开）。

A-grasp1-axis-shift4mm-v44失败：输入/物体沿轴偏移-4mm时翻转、0循环。A-grasp1-unshifted-v45对照保持原抓姿1，10s完整1轮、2mm端点通过、世界漂移6.30mm/0.215rad稳定，因此后续保留原抓姿1，不用4mm偏移。negative端向下、刀轴朝上可让重力保持闭刀；原抓姿1的手网格桌面净空为0.885mm（其他原姿势此方向穿桌），因此只把候选几何预检下限设为0.5mm，实际桌接触仍记录/审查；任务成功阈值不变。

G2负端着桌在75cm桌面候选yaw60/75/90/105中没有同时满意的持刀/功能两端IK。显式比较80/85cm后，80cm的yaw75/90均可达。新增table-height参数保留默认75cm，80cm作为正常更高桌面的单列条件，未改手/刀物性。80cm初始接近/抓紧/抬升全可达，转竖及下降连续IK位置残差<1.7微米、姿态<9e-6rad（negative-end-table80-path-v47.json）。A-grasp1-table80-v47（PID3624735）正在20s复测，确认A后再开始实际B。

计划B参数：table-height .80、grasp1、原edge-pinch8抓取、upright-end negative、upright-yaw75、table-regrasp-plan functional-open-negative-grasp1-v47.json、level-standing-knife、measured-release，其余10/20/1臂伺服不变。该B尚未启动。


## 19:44 CST 闭刀竖起成功，转腕失稳定位（v48–v53）

A-grasp1-table80-v47完成20s两轮：四端点2mm通过、40.019mm行程、6.30mm/0.215rad漂移稳定。负端着桌仍明确为80cm桌面单列条件，未更改手刀物性。原A/B/C固定基线结果保持不变，尚无B/C完整成功。

v46未真正执行找正，原因是旧SciPy单向量align_vectors产生非最短旋转（意图0.0615rad却返回0.2985rad），导致37.5mm腕位移预检中止。已实现并验证minimal_alignment，实际校正7.13mm，在25mm边界内；parallel/antiparallel及实测姿态审计见minimal-tilt-audit-v49.json。不能将此记为物理找正失败，修正后的正端着桌尚未重跑。

v48负端着桌合并倾转/yaw中掉落；修复支撑判据，不能只因掉在桌上仍有接触就认为端面支撑成立，现需倾斜<0.15rad、刀中心高于桌面60mm以及最后1秒接触≥80%。v49重求12mm预压同时轻微改变几何，故不是纯压力对照；新增retarget_g2_pinch_pressure.py仅改变闭合目标，严格保持wrist/touch/open后，v50仍转竖失败。v51先yaw后倾转的CPU路径预检失败（120mm/0.433rad），因shell未短路误启动，已立即中止，标PreflightAbort，不作为物理结论。

v52改为先倾转到竖直、再yaw，保持原8mm侧夹。已成功倾转且五指接触、滑块闭合；随后yaw到75°时约20s失去接触并掉落，全部部分轨迹和视频保留。关节命令最高速度未超G2限速，但yaw有较快关节变化和跟踪误差，尚不能据此认定唯一根因。

B-negative-slow-yaw-grasp1-v53（PID3742855）只将最后yaw从5s延长15s，其他几何/物性/控制不变，用于区分速度/跟踪因素。未训练新模型、未做20扰动验收。原88339仍运行，最近只读GPU负载34%。v39之后尚未进入Release，下一份增量包合并排除v1+v2已发布清单，避免重复上传。


## 19:50 CST 慢速yaw通过，补齐全臂桌碰撞门禁

v53与v52前540帧相同，15s转腕保住五指接触和闭刀，转腕末刀轴倾斜0.0136rad。随后下降并非再次掉刀：G2腕部/前臂先碰桌，刀中心停在0.963m、刀端距80cm桌约90mm，端面接触0%。原先只查手指桌碰撞不足以说明G2整条路径可执行；原始物理已有robot_table_contacts，已据此定位并保留此失败。测得驱动误差最大约0.47rad，不应继续下压。

新增g2_table_collision.py按导出碰撞凸包、完整G2 FK与实际桌盒做分离轴检测（面法向和棱边叉积），在机械臂/手掌路径加入2mm规划余量；实际任何臂/掌桌接触立即中止并保存轨迹。v53最终命令几何穿桌：arm_r_link5/6/7及手掌，最大约51mm。负端着桌原功能抓姿1本身还存在G2腕link7约3mm实质穿桌（2mm余量后5.1mm），因此不再仅凭手指净空0.885mm宣称该路线可用。

几何考虑向刀上端平移60mm侧夹，可清除取刀腕部碰桌，但index超出刀端、需实际验证另四指，且原功能抓姿的腕碰桌仍在；仅保存edge-pinch8-upper60-v54.json候选，不启动物理。9个不转yaw的桌面位置端态均未通过G2 IK，见negative-no-yaw-endpoint-search-v53.json；不将预检不通过计为物理试验。

回到正端着桌：原三个功能抓姿的G2全臂/掌几何均通过桌碰撞预检。B-positive-corrected-level-grasp0-v54（PID3777023）只重测已修复minimal_alignment的找正/卸压/重抓路线，75cm桌、原8mm侧夹；此次only-grasp明确不调用策略。该方向会被动打开滑块，不能计作策略伸出，若重抓通过仍需经正常腕部重力姿态使其被动回闭再验证接管，不直接驱动滑块。

评分修正：操作中真实掉落或刀桌接触使whole_success为False，不能仅以手内相对位姿小而通过；循环只否决发生掉落/碰桌的那一轮，保留此前完整轮数。原A47重算仍通过两轮，合成注入最后帧桌接触的纯评分诊断得到整段失败/1轮，见operation-drop-score-audit-v54.json；未改物理轨迹或旧报告。


## 19:54 CST 正端找正后的释放判据对照（v54–v55）

v54实际找正执行完四次，刀桌支撑100%、臂/掌/手指无桌碰撞；倾斜从0.0615rad降至0.0489rad，但未达到原0.02rad控制放行阈值，故中止在释放之前。不能说已松手成功，也不是再次掉刀。实际最后夹持拇指/index/ring/pinky有接触。

按当前35g两刚体的实际位姿计算重心投影，v54在建模19×8mm端面内的最小余量0.908mm；v41找正前只有0.466mm，原v41松手后投影越界并倒下。新增显式standing-level-gate=support-projection对照，要求实际刀桌接触≥80%、总倾斜<0.15rad、两刚体重心沿重力投影距离端面边界≥0.5mm。这是释放前的几何候选筛查，不能代替实际无手支撑的稳定性。保留默认tilt门禁及v54失败，不改变控制幅度或任务操作判据。

B-positive-com-release-grasp0-v55（PID3792954）只改变上述放行判据，接着执行实测卸压/开手/撤离/功能重抓。仍only-grasp，不调用策略；滑块被动打开问题尚未解决。当前分支已推100b1fa，v55新增判据代码未推。下一次增量Release拟收v39之后的结束试验和代表视频，排除前两包，不重复历史权重。


## 20:02 CST 正端释放通过，功能闭合没有建立对夹（v55）

v55完成真实平放取刀→正端放回桌面→找正→卸压/释放→撤离。松手后全部五指无接触，刀具在桌面独立保持竖立（中心0.823500m）；功能开手接近时腕位姿约1.1mm/0.00084rad误差，没有机器人桌碰撞。但闭合阶段拇指接触0帧，index仅15帧、ring7帧、其他很少；重新抬手后刀留在桌上，故整个抓取/接管失败、未调用策略。不是完整成功，也不是刀具从桌面掉落。

原闭刀功能抓姿拇指接触在刀具局部y≈6.89mm、z≈−6.91mm，接近闭合滑块端部；此时滑块已被动全开，该处只剩y=4mm的刀身表面。因此缺少拇指对夹与本次实测相符，但不排除其他控制因素。

下一步有界地比较抓取阶段的身体夹持目标：让拇指接触刀身外角，避开滑块通道，四指从背面闭合，只改变电机目标，不改物性/策略。positive角的首次CPU几何IK失败27mm，不启动物理；negative角正在CPU预检。新增plan_g2_body_regrasp.py保存几何门禁结果。新runner允许读取明确的close_q/touch_q，并在relift末检查真实抬升及对夹；失败即中止，避免继续空手搬运。

被动回闭后备阶段已实现为可选gravity-close-before-takeover，先在空中用G2电机把刀轴转向上，静置3s，再恢复原功能目标和操作姿态；几何预检可达/无桌碰撞，但尚未在物理中执行。滑块始终刚度0且无外力，回闭要求2mm误差，不能算冻结策略操作成功。当前还没有任何新完整B/C成功，未训练、未20扰动。


## 20:05 CST 刀身外角闭合候选进入物理（v56）

negative外角touch/close几何可达；12mm开口的拇指IK误差1.923mm未通过1mm预检，改为显式8mm开口后误差<10μm、全过程手指桌面几何净空14.19mm。另有刀身正面候选几何通过，但可能阻挡滑块回闭，暂未物理运行；positive外角不可达保留失败。

B-body-corner-reclosure-teacher-v56（PID3852334）保留v55成功的取刀/放端/释放段，在功能接近时用negative外角拇指+四背面指，先到触碰目标再2mm电机目标过行程闭合。若重新抬刀通过才继续搬运、19+2秒有界被动回闭/恢复动作及冻结teacher20s。实际运行结果待收，任何阶段失败均不能算完整成功。新阶段仅用G2/手指电机目标，滑块不驱动；物性/权重仍原样。

本轮准备增量Release v3收v39–v55已结束17项及代表性完整无字视频，v56在途单列，不覆盖前两版。


## 20:08 CST 第三份增量Release已核验

https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-tabletop-support-20260925-v3 已发布并逐项校验6附件大小/SHA256。新增17项结束试验，15.2MB证据包，排除前两份54项；v55源码恢复3866文件通过。三个完整无字视频为A47预置成功、v53下降碰桌失败、v55独立立刀但功能重抓失败。快照v56仍在途，未纳入结束试验。代码已推0a38ba0；新阶段仍不代表完整B/C成功。


## 20:12 CST 外角夹持未能抬刀，正面对夹对照

v56外角夹持建立五指接触，但relift中刀只升约0.8mm便失去接触，刀回到竖立桌面；无手桌碰撞。新relift门禁正确中止，未执行被动回闭或teacher。接触法向不对称仍可能影响稳定性，不能只据此说压力不足。

v57只把thumb改到刀身正面，与四指背面对夹；相同8mm开口/2mm电机目标过行程、原腕部功能关系，新增几何误差<10微米、桌面净空14.19mm。该诊断only-grasp，不运行策略；正面拇指可能阻挡被动回闭，先查抓持是否建立，再决定有界的倾斜承托/松拇指对照。v57已启动，PID见B-body-face-regrasp-only-v57-process.json。


## 20:15 CST 后备被动回闭方案的几何预检

v57正面对夹仍在运行，尚未验证抬升。为了避免正面拇指挡住滑块，新增可选gravity-close-support=tray：让刀轴向上30°，重力分量同时把刀背压向四个支撑指，短暂开拇指后靠重力回闭，再恢复原功能目标。全程只有机器人电机动作，无滑块驱动；此阶段尚未物理执行，不计成功。

目标重力knife-local为[0,−8.496,−4.905]m/s²。原最短转腕路径末端触及G2限位；有限比较world yaw −30/−15/+15/+30后，+30方案全程位置残差<0.22微米、最小关节余量0.208rad、无臂/掌桌碰撞。world yaw保持刀内重力方向不变，仅改善G2可达性。预检文件passive-tray-yaw-preflight-v57.json；若v57实际抓持成立，再按此方案做物理对照，不直接扩大训练。


## 20:18 CST 连续功能重抓与搬运首次通过（v57）

B-body-face-regrasp-only-v57完成真实平放取刀→端面支撑→完全松手→功能腕姿正面对夹→重新抬升20cm→搬运→停稳。最后1秒全部帧thumb+≥2支撑指接触，刀桌无接触，相对漂移3.96微米/0.000125rad；抓取到接管位置通过1/1。相对原功能抓姿6.06mm/0.0670rad误差单列，不能用稳定性掩盖。滑块仍约0.0164m（接近全开）；此次only-grasp，操作未请求，整段成功尚未评估，不能写成0/1或完整成功。

B-face-tray-reclosure-teacher-v58（PID3914214）保留相同抓取段，新增经过G2几何预检的30°倾斜承托、world yaw+30°、仅拇指暂开以允许重力被动回闭。随后用有限驱动在2秒内平滑回到原功能电机目标，再8秒回操作姿态，停稳积累真实历史。恢复的是电机目标，不是写入缓存关节/物体状态。若回闭/握持通过，接冻结teacher外部时钟20秒；任何失败保留且不计学习操作成功。原手刀物性及权重不变。

最新发布仍为v3（到v55）；v56失败和v57抓持成功尚未上传，待下一增量。没有C新成功、未20扰动、未训练。


## 20:23 CST 当前代码A回归通过

A-current-guards-headless-v58完成20秒2轮：四端点<2mm、行程40.0897mm、固定参考世界漂移7.7445mm/0.1498rad，无掉落且稳定。与A-g2-integral-v12逐帧q/arm_q/object/wrist/slider/targets/action完全一致（a-v12-v58-physics-parity.json）；新增碰撞门禁/回闭可选代码未改变原A行为。A已结束，v58实际桌面流程继续。最新远端.106/.93:30147均Connection refused，未更改远端或原训练88339。


## 20:27 CST v58被动回闭与返回通过，teacher待收

v58实际承托阶段回闭到slider下限，hold检查误差3.73e-9m；期间拇指接触为0、四支撑指接触保留。原功能电机目标通过2s真实驱动恢复后五指接触，返回操作姿态时slider仍在闭端约0.03mm内、刀身保持。当前已进入settle_history，将以固定接管参考/冷RNN/实际50帧历史开始冻结teacher。尚未收齐20s操作，不能提前宣称B成功。


## 20:31 CST 连续B58已接teacher但回收差1–2mm未过线

v58完成从桌面开始105秒连续物理：抓取/真实重抓/承托被动回闭/返回均成功，冻结teacher操作20秒、行程37.994mm、无掉落，固定参考漂移3.558mm/0.1526rad稳定。两次伸出误差1.922/2.016mm；两次回收末段最大误差10.946/12.332mm，最终误差约10.83/10.84mm，超过预定10mm标准，故0完整合格循环、条件操作0/1、全段0/1，不能放宽阈值报成功。

A/B末端审计a-b-retraction-endpoint-audit-v58.json：B手内刀沿初始刀轴偏移约5.61mm，旋转0.125rad；原A刀轴重力分量−0.481m/s²（帮助回收），B实际+0.488m/s²（帮助伸出）。B回收末段thumb仍输出动作，多数关节未达限位，不能直接归为硬关节限位。存在重力方向反转，仍不认定唯一根因。

有界操作姿态对照：固定腕部位置，将名义刀轴上倾10°，其余手刀参数/模型/目标/5秒时钟不变；改变的是G2目标姿态，不是驱动物体或滑块。IK残差<14nm/8.3e-8rad。A-operation-up10-v59先验证新姿态A，PID见process.json；A通过后再发同一B流程。新矩阵operation-knife-up10-v59.json及设计说明保存。B/C仍未完整通过，未20扰动或新训练。


## 20:34 CST 上倾10度A通过，B姿态对照启动

A-operation-up10-v59通过20秒两轮、四端点2mm内，世界漂移6.519mm/0.1557rad稳定。B初始接近/抓取/抬升IK与原v58最大差4.6e-9rad，见operation-up10-acquisition-ik-parity-v59.json，非换初始抓法。B-up10-tray-teacher-v60已启动，PID见process.json，除最终操作姿态上倾10度（同时影响前往该姿态/承托往返路径）外保持v58条件。待判断是否修复回收不足；不改10mm阈值，不根据单项对照认定唯一原因。


## 20:38 CST 第四份增量Release已核验

https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-tabletop-handoff-20260925-v4 已发布，5附件大小和SHA256均通过；新增5项结束试验，排除前三包71项，证据9.7MB。完整62秒功能重抓诊断及105秒取刀→teacher回收未达标视频已按结果命名，均无文字。B58源码恢复3867文件一致。分支5e29c7a。B60仍在运行，不计为成功或结束试验。


## 20:43 CST B60仅搬运IK失败；补做从实际末态出发的整路径筛查

B-up10-tray-teacher-v60已真实重抓并重新抬起，但其负号肘部IK分支在直达上倾10°操作位时触及关节限位，残差2.32mm/0.0114rad，门禁在第1650帧中止。没有执行新姿态teacher，不能认为上倾重力对照无效。之前从A静态IK分支出发的局部路径可达并不适用于B实际分支；已分别记录actual-B-operation-to-up10-v61.json和fixed-wrist-posture尝试，均未放宽门禁。

从B60实际抬升末态的电机参考出发，有限比较4个world yaw与6个±20mm位置候选；全路径保留table凸包碰撞和IK门禁。yaw+15与+30均可达，进一步沿B58实测手刀关系核验承托和返回路径也通过。选+15为较小转动，即操作yaw105、保留刀轴上倾10°；world-z旋转在代数上完全保持手内重力方向，便于区分可达性与重力效果。路径部分经过源关节限位，不能称有充足裕量，仍需物理验证。

A-up10-yaw105-v61先验证该最终操作位，PID见process.json；A通过才发B。矩阵operation-up10-yaw105-v61.json和up10-continuous-pose-candidates-v61.json/up10-yaw-tray-roundtrip-v61.json保存。最新完整B结论仍是v58稳定但回收略超10mm，无C新成功或20扰动。


## 20:46 CST 最终候选操作位A通过，B62开始

A-up10-yaw105-v61完成20秒2轮，四端点2mm均过、漂移6.398mm稳定。B-up10-yaw105-teacher-v62已启动，PID见process.json；从实际抬升末态出发的搬运、承托和返回IK已预检通过。此B结果未知，不把A等价当B成功。若B62端点/握持/稳定通过，下一项是相同参数、同一物理抓取段的C学生理想初始化；尚未冻结20扰动方案。


## 20:56 CST 新操作位失败与保留抓取路径的后续对照

v62从正常桌面到接管仍抓取成功1/1，但冻结teacher操作后刀身大幅翻转（2.056rad）、世界漂移42.26mm，四端点10.659/29.382/11.036/28.809mm均不合格；未触桌或检测到真正掉落，归类operation_pose_escape，不能把“仍有接触”当稳定。完整105秒视频、轨迹保留。接管关系相对原功能抓姿8.535mm/0.219rad，较v58的6.016mm/0.125rad更偏，改变搬运/承托路径同时改变了末态，不能单独归因重力。

新增可选post-acquisition-pose：保持v58成功获取/承托/回闭/返回路径完全相同，仅在其后用4秒真实G2电机调整腕姿，再停稳、接管。限制额外位移≤20mm/旋转≤15度，手指电机目标保持，零物体状态写入。当前选择上倾5度、原yaw90；从v58真实返回末态电机参考预检，全路径IK位置<12nm/转角<6e-8rad且无臂掌桌碰撞（post-acquisition-up5-preflight-v63.json）。部分源关节边界仍很近，非大裕量方案。A-operation-up5-v63正在先验新腕姿；通过后再发相同旧抓取路径+B后置调整，不改10mm标准。

新增audit_g2_handoff_replay.py从50帧真实执行历史重建冻结策略、仅清零一次RNN，逐帧核对观测/动作/目标及固定参考；B58全部600帧三项误差均0（frozen-replay-B58-v63.json）。轨迹审核FK最大1.06微米/2.81e-6rad，关节命令与实测速度均不越源限速，角度浮点超限2.55e-7rad。该离线回放只证明接口执行一致，不增加物理成功样本。


## 20:59 CST A63通过，原获取路径后置调整进入物理

A-operation-up5-v63在上倾5°/yaw90下20秒两轮、四端点<2mm、世界漂移7.113mm/.1564rad稳定。B-original-path-post-up5-teacher-v64已启动（PID见process.json），仍正常75cm桌面、原B58所有获取/被动回闭参数；新增4秒G2腕部上倾5°在回闭返回之后，停稳历史之前，连续物理无重置。结果未知。

已将功能正面对夹及两个诊断操作位JSON加入Git可复现资产目录。新增小变化执行工具run_g2_small_variations.py，但未生成/执行验证样本；它要求固定A/B/C全段稳定通过后才能声明10个共享摆放×B/C共20次任务，范围x/y±5mm、yaw±2°，固定seed2026092501，每次来源于校验过的冻结源码pin。声明与状态分开、规划失败也保留计入整段分母，不调参重抽样。用当前失败B/C实测门禁拒绝，未误发任何验证。仍没有新训练。


## 21:04 CST 机械臂自身几何补查

新增audit_g2_self_clearance.py：按实际G2右臂关节轨迹、导出碰撞凸包及完整零位固定机构做SAT检查，包含面法向与边叉积；只排除两条关节边以内的连接壳体/安装接缝，以及另行处理的右手指自接触。B58每秒取样、末帧共106帧，414个候选链对均未检出>0.1mm凸包重叠。记录self-clearance-B58-stride30-v64.json；这只是采样诊断，非连续全路径认证，也没有更改源资产关闭自碰撞的物理设置。初版一次性投影阵列占8GB，已只中断该离线审核并改为256轴分块/先测面分离，完成相同SAT判据；原训练及B64均未受中断。

B58/B62接管电机目标逐项相同，实际受力关节角/接触关系不同；B62操作0.20s首次拇指失联、0.233s旋转超过0.25rad、1.733s漂移超过10mm（B58均未发生）。记录B58-B62-loaded-handoff-comparison-v64.json，只作为末态/接触敏感性证据，不认定唯一原因。


## 21:12 CST 后置5度仍未通过窗口，轴向3mm获取对照

B64从桌面起共109秒，抓取1/1、条件操作0/1、全段0/1。四端点末0.3秒最大误差为2.122/10.342/2.225/12.251mm；两次收回最后一帧虽为9.782/8.835mm，但不能替换预定窗口判据。无掉落、世界漂移3.898mm/.1383rad稳定，仍0完整合格循环。不能按某一早期日志帧进入10mm便计成功。

B58与B64前2490帧直至gravity_close_return的q、arm_q、物体/滑块/腕位姿、目标、接触计数全部逐项相同（B58-B64-acquisition-prefix-parity-v65.json）。B64冻结策略离线重放600帧观测/动作/目标误差均0。后置5°未导致B62那种翻转，但不足以通过回收窗口。

新增plan_g2_body_regrasp --wrist-axis-offset .003：仅把功能重抓腕相对刀轴沿+z移动3mm，尝试部分抵消接管时约6mm位置偏差；不修改前段侧夹、手指电机目标、物性、权重、20秒时钟。重算四组手指目标float32与原计划完全相同，几何手桌净空11.187mm，实际withdraw末态起的功能接近/重抓/再次抬升/搬运IK位置<0.4微米、转角<2.55e-6rad且无臂掌桌碰撞。后续自由物体/承托仍需实际验证，不能据预检宣布末态已改善。

B-axis3-post-up5-teacher-v65已开始（PID见process.json），保留B64后置5°及其余设置。完整B/C仍未通过、未声明或执行20变化、无新训练。下一步收v65实际末态与全程评分；若通过才发同条件C并标记理想初始化。

复现该有界诊断（使用新的name，按前文下载既有冻结权重）：

```bash
python -m scripts.plan_g2_body_regrasp --thumb-corner face --gap .008 \
  --squeeze .002 --grasp 0 --wrist-axis-offset .003 --output /tmp/g2-body-axis3.json
python3 -m scripts.launch_g2_trial --name B-axis3-reproduce-001 -- \
  --group B --operation-yaw 90 --yaw 180 --dx -.05 --wrist-posture -.7 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan assets/robots/g2_wuji/plans/edge-pinch8.json \
  --table-supported-seat --upright-yaw 250 --table-regrasp-plan /tmp/g2-body-axis3.json \
  --level-standing-knife --standing-level-gate support-projection --measured-release \
  --gravity-close-before-takeover --gravity-close-support tray --gravity-close-yaw 30 \
  --post-acquisition-pose assets/robots/g2_wuji/plans/operation-knife-up5-v63.json \
  --video --camera hand \
  --teacher weights/g2-frozen/wuji-core-teacher-student-20260924-teacher.pth
```


## 21:15 CST 第五份增量Release已核验

https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-tabletop-operation-20260925-v5 已发布，5附件大小和GitHub SHA256逐项一致。新增5项结束试验（B60/A61/B62/A63/B64），证据11.6MB，排除前四包；B64源码/输入恢复3872文件核验通过。无文字视频分别保留105秒翻转失败与109秒收刀窗口失败。代码已推da4d69d；B65快照时仍在途，未列作结束/成功。B64额外110帧/414链对自身凸包采样也未检出重叠，仍不是连续认证。


## 21:22–21:25 CST 固定B首次完整通过，冻结C开始

B-axis3-post-up5-teacher-v65从正常桌面连续109秒（获取89秒+冻结teacher20秒），抓取1/1、抓取后的操作1/1、全段1/1；外部时钟两轮开合，四端点末0.3秒最大误差1.895/7.038/2.038/7.647mm，全部10mm内，无掉落且固定参考世界漂移4.114mm/.1592rad稳定。2mm严格诊断未全部通过。此次为调试中选出的单案例，不能作为泛化成功率。相对原功能抓姿位置差由B64的5.948mm降到3.624mm，旋转0.1285rad；这是改善接管几何后得到的结果，不认定唯一原因。

B64/B65前1080帧直至withdraw完全一致（B64-B65-acquisition-prefix-parity-v66.json）。B65冻结回放600帧观测/动作/电机目标误差0；实际腕FK约1.06微米/2.79e-6rad，命令与实际速度无超源限速。110帧自身凸包采样未检出重叠。

机器人/桌面并非全程零接触：approach有8帧、close有46帧拇指/小指碰桌，碰撞网格在桌面范围内最低0.211mm穿入，源PhysX contact_offset=2mm；没有臂/掌碰桌，抬起及操作阶段没有桌面支撑。这些如实记录在B65-finger-table-contact-clearance-v66.json，不能写成“手指从不碰桌”。仅是仿真接触与网格估计，不能当硬件触觉力标定。

C-axis3-post-up5-student-ideal-v66已在21:22:23 CST启动（PID7325，PID计数回绕后的小编号正常；原训练88339仍活跃）。launcher直接复制B65校验过的源码pin，两者SOURCE_SHA256清单哈希完全相同4b63cd7459d02e73f4d9788ebce5a3d6507fab3f394ce38863a5d73a425dba49，参数仅group B→C。Student冻结权重保持；实际50帧停稳历史、RNN只清零一次、接管初始物体真值明确理想初始化。结果待收，不提前宣布C成功。

若C同样通过，先做实际前2670帧一致性与冻结回放/实时真值不变性审计，再声明10个位置×B/C共20次的既定小变化。使用A-operation-up5-v63 / B-axis3-post-up5-teacher-v65 / C-axis3-post-up5-student-ideal-v66。当前没有声明或抽取验证样本；还没有新训练。B65完整无文字视频已保存continuous.mp4，待和C一起增量发布v6，不覆盖v5失败证据。


## 21:33 CST 固定A/B/C收齐通过；20次小变化已预先声明

C-axis3-post-up5-student-ideal-v66完成109秒连续桌面流程：抓取1/1、条件操作1/1、全段1/1，两轮10mm基本到位且稳定；四端点4.914/5.413/6.656/4.827mm，行程37.082mm，固定参考漂移5.185mm/.2355rad，无掉落。2mm诊断未通过。这是仿真定位与物体初始真值条件下的单案例，不是可部署或泛化验证。A63同一最终5°腕姿通过2mm及稳定；B65通过10mm及稳定。汇总abc-current-continuous-v67-final.json，旧pending快照保留。

B65/C66前2670帧直至接管完全相同，实际物性physics.json也字节相同；C冻结重放600帧的观测/动作/电机目标及实时物体真值扰动不变性误差均0。实际50帧历史均为settle_history，动作0；RNN接管时清零一次，初始目标/观测固定。依据B65-C66-acquisition-prefix-parity-v67.json、frozen-replay-C66-v67.json。

run_g2_small_variations.py已在固定ABC通过后声明10组共享摆放×两策略，共20次；x/y±5mm、yaw±2°，seed2026092501。文件runs/g2-tabletop-v1/g2-small-placement-v1.json及公开副本research/g2-small-placement-validation-v1.json，SHA256 20f313a7f96681241a71a6d83b8f9a8db057947f888dbaa9caa7b718a8c5b7a1。将先提交/推送声明，再启动；不修改该清单或失败样本，不在本组上调参。每次复制C66经哈希校验的冻结源码pin，保留全部日志、原始轨迹和视频；初始规划失败也保留在整段分母。当前只是已声明，尚未完成验证。

复现并继续已声明验证：

```bash
python3 -m scripts.run_g2_small_variations run \
  --manifest runs/g2-tabletop-v1/g2-small-placement-v1.json --concurrency 2
```

状态/分组结果写g2-small-placement-v1-results.json；不要并发启动多个driver。遇中断先核对driver和子进程，单个driver可恢复未启动项，已失败项不重跑。A/B/C权重及控制无新训练。新成功视频待增量Release v6，v5失败证据保留。


## 21:35 CST 验证driver已启动，冻结方案保持

预声明清单已先提交并推送GitHub 86b191b，随后21:34:47 CST启动唯一driver PID67920，记录g2-small-placement-v1-driver.json；初始B/C子进程为g2-small-placement-v1-00-B/C，2路并行，源C66冻结pin，原训练88339保持、整机GPU约99%。清单及public副本SHA不变，不能改样本或调参；driver/launcher源码SHA也写入driver记录，不要在途中修改或启动第二个driver。

结果进度读g2-small-placement-v1-results.json，完整日志在各试验同名.log；先核实实际PID，不能据旧文档重启。首批尚未结束，不当作20次成功。新简版可复现报告research/g2-tabletop-fixed-baseline.md给出A/B/C数字、普通桌面端立路线、所有student输入来源及原始文件位置；完整开发史仍保留。


## 21:41 CST 固定成功Release v6已核验；首对验证失败保留

https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-tabletop-fixed-abc-20260925-v6 已发布并核验5附件大小/SHA256；新增B65/C66两项结束记录，8.15MB证据，排除前五包。C66源码恢复3874文件一致，两条无文字视频各3270帧/109秒。新简版README含ABC数字、数据来源和可执行命令。v7打包需额外排除release-fixed-abc-delta-v6/evidence/MANIFEST.json，不能重复上传v6。

预声明首个共享位置（dx+1.088mm、dy+0.750mm、yaw+0.393°）的B/C均在第720帧support_settle中止：刀桌接触100%但刀轴偏竖直1.605rad、刀心高度0.75655m，已经倒在桌上，不是正常端立。两次均在策略接管之前失败，不能归类为teacher或student操作失败。仅当前2/20结束，获取到接管0/2、条件操作0次，全段0/2，不能外推最终成功率。视频和partial-trace保留，driver已继续第01对；不修改清单或方案。

独立工作分支代码/预声明已推，v6目标c77754a。验证driver PID67920仍运行；后续必须读最新results.json、查实际子进程，全部20次结束后生成分组比率、端点/行程/掉落/漂移和失败分类，并发布v7新增证据/代表性失败。暂不凭首对失败改参数；下一项改进建议应等完整分布再判断。goal仍active，未调用complete。


## 21:49 CST 验证失败发生阶段与原始轨迹审计

20次冻结验证继续，当前已完成前4个共享位置/8次，全部中止，driver PID67920和第04对真实子进程正常。新增summarize_g2_validation.py只读原始轨迹、source pin和命令，核对每项声明偏移、冻结物性、所有源码文件SHA、滑块目标恒定/刚度0、视频帧数及B/C实际前段一致；操作阶段若未到达，所有端点/行程/漂移指标为null，获取期间滑块移动单列。

首3对原始轨迹显示初次抬起均成功，但在stand_orient转腕阶段失去手指接触并掉落，后续support_settle才触发中止。00/01/02确认落桌时间分别为15.600/15.433/15.467秒，转腕开始后约2.4–2.6秒。00无接触自由落体期间相邻控制帧竖直速度差约−0.32m/s，与重力30Hz一致；没有物体状态写入或瞬移。新增small-placement-audit-progress-v1.json保留快照（仅首3对），源和物性检查全部通过。

对应末端目标转动约125–127°，与固定成功例126.56°接近；首3例arm-plan最大变化0.034–0.048rad，未发现大幅IK分支跳转。这些证据支持获取转腕接触敏感是当前瓶颈，仍不认定唯一物理根因。small-placement-first3-turn-diagnostic.json及独立图small-placement-diagnostic-progress-v1.png从轨迹生成，视频仍无文字。暂不改变方案，等待全部20次收齐后统一结论。


## 21:56 CST 验证继续与全控制帧自身几何核查

固定B65全部3270控制帧、414个非相邻机构链对的凸包SAT检查未发现重叠，见self-clearance-B65-all-control-frames-v68.json。检查仍排除连接壳体近邻和右手指自接触，也不证明帧间无碰撞；没有更改源自碰撞配置或物理运行。

当前前6个共享位置/12次已结束，均在策略接管前失败；第06对仍活跃并已经过转腕到下降阶段，尚不能提前判断。首5对独立完整审计small-placement-audit-progress-v2.json确认初次抬起每组5/5、到接管0/5、条件操作未评估（分母0）。所有源码SHA/物性/预声明偏移和视频帧数均核验。

接触诊断small-placement-first6-contact-diagnostic.json显示转腕中拇指仍主要触刀身，滑块被动位置/支持指接触时序却随小偏移改变；不把这一相关性当唯一失败原因。初步证据集中在获取转腕，而非冻结策略/接管接口，未启动任何新训练。待全部20次终态后统一出最终报告。交付核查表research/g2-tabletop-delivery-audit.md已逐项列出证据与剩余验证/发布项。


## 22:00 CST 16/20原始轨迹审计，失败分类分化

small-placement-audit-progress-v3.json已核验前8对/16次：B/C各初次抬起8/8、获取到策略接管0/8、条件操作0次（比率null）、整段0/8。编号00–05及07在stand_orient空中掉刀；编号06则保持到桌面，支撑接触100%、刀心0.82088m，但倾角0.43997rad（25.2°）超过原0.15rad，未进入找正/松手，分类end_support_tilt_exceeded。不能一律写成未抓起或所有刀都掉落。

汇总脚本新增明确端立倾斜分类，检测掉落时区分计划放端/主动释放，保留原始guard消息；所有判断仅离线读记录，不改变冻结验证。driver/launcher清单哈希未改变，编号08的两物理进程正在运行，之后仍需编号09，不能提前发布最终成功率。最后两位置完成后生成require-complete最终审核并制作v7；代表失败建议保留00空中掉刀和06端立倾斜，两者24秒无文字视频。


## 22:08 CST 20次全部收齐并通过原始证据审计

验证driver及所有20个子进程正常终态，原训练88339仍活跃。最终small-placement-validation-final-audit.json：B/C各初次抬起10/10、获取到策略接管0/10、整段0/10；条件伸缩分母0，标为未评估。每组9次stand_orient转腕掉刀、1次端立倾斜0.43997rad超0.15rad门禁，均在第720帧support_settle中止。全部视频各720帧/24秒，共14400帧；10对B/C实际获取逐项相同。没有改参数、剔除或重跑样本，源码所有文件/物性/预声明偏移/视频帧数核验通过。

最终报告research/g2-tabletop-final-report.md及20次CSV已生成；固定A63/B65/C66仍为10mm/稳定成功单案例，泛化验证明确失败，C仍理想初始化。独立诊断图small-placement-validation-final-diagnostic.png目视核对完毕。所有原始轨迹和视频保留；拟v7增量只收20个新case，代表视频选00空中掉刀和06端立倾斜，不重复前六包。

本轮无新训练。下一项仅建议对获取转腕时长5→10秒作固定位置+两个已观察失败位置的6次对照，方案未执行，不扩大RL或改本组结果。driver退出后，修正未来跨环境复现的launcher参数显式沿用冻结命令Python路径（--python command[0]），不影响已结束试验或其源码pin；原执行driverSHA记录保留。当前剩余工作仅v7上传/核验、最终文档和goal交付审计。


## 22:13 CST v7发布核验与本轮交付收尾

v7已发布：https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-tabletop-validation-20260925-v7 。8附件大小和GitHub SHA256全部相同；新增且仅新增20次预声明试验，15.1MB原始证据，排除前六包。还逐一从tar归档读取全部20次trace、接触、物性、计划、失败，与本机原件SHA相同；最终审核和清单也一致。编号06恢复3874源码/输入文件通过。两个24秒无字代表失败、20次CSV、最终报告、诊断图和复现README均已上传。公开核验记录research/g2-tabletop-publication-verification.json，原始核验在release-validation-delta-v7。

固定A/B/C两条109秒成功视频仍在v6，未覆盖旧成果。验证driver和20子进程全部终态，原训练88339实查仍运行；本阶段没有新训练。所有交付项已在research/g2-tabletop-delivery-audit.md逐项复核。下一步仅建议有界获取转腕时长对照，未启动；当前固定基线完成、小范围泛化失败、student理想初始化、真机未验证这四点不变。待最后分支推送及goal工具状态更新，本轮基线/20次评估/增量交付工作即可关闭。
