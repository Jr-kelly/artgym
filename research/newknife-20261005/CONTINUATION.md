# 新刀 Goal 续接（2026-10-05 当前开发轮，未交付）

先核验进程和 STATE.json。真实副本是本目录所在仓库；原 `/data/research/artgym` 不做实验。禁止子代理、真机命令、私有照片/附件公开。Goal active，无预算/最低运行时间；不能把失败当成功。所有阶段用 `scripts.record_wuji_newknife_event.record` 维护中央 WUJI_GOAL_HANDOFF.md 和 runs/wuji-goal/journal/events.jsonl。

## 已有不可重复丢弃的工作

- 当前模型资产 `nominal-v5`，144×19×8mm 主体，32×7×2mm 滑块，55g 两运动链接，初始q0、滑轨[-10,+55]mm。75gf=0.73549875N；固定夹具校准有效，变化曲线是工程假设。详见 RESISTANCE-CALIBRATION.json。
- 实测法向力、仿真接触法向力、制动容量、真机 B/C 必须分开。真实机器人没运行，真力曲线没有恢复。
- 原 S120 SHA：ad16a153c27eb01567c14422ca8ed23e5bebfc6e1c901683031f245631944d2a。旧 highload/traction 结果不改。
- 已建独立 git，branch feat/wuji-newknife-20261005；提交720c5f6、e05c583、0dd5d6c。尚未发布。原 highload 复制来的 dirty 文件不要纳入提交。新源码仍有未提交更新。
- `capfront-v2` 是目前可靠的原取刀 preparation。四个有完整视频的基线、诊断和后续结果均保留在 `runs/newknife-20261005/continuous/`。汇总工具 `summarize_wuji_newknife.py`。当前没有全部通过的双循环。
- 四组远端训练已完整结束：constant/variable × seeds2026100511/12，各128env、100update、819200transition；thumb-head-only、固定S120支撑映射，压力proxy1.2N，摩擦固定0.8/1.8。全部权重、日志已经同步本地 train/，哈希在 THUMB-TRAINING-RESULTS.json。不得盲目续训。
- 训练存了 scheduled_target_holds=True。最初 u50 原生复验未启用，保留为 unmatched。发现后修复 `run_wuji_newknife.py` 读取保存的 scene_spec 自动启用。远端最初 final-* 中途终止；随后 faithful-final-* 的8次完整复验已经同步本地并验证都有该flag。0/8通过；第一轮约9–11mm，第二轮部分27–29mm，返回和roll仍失败。THUMB-FAITHFUL-NATIVE-RESULTS.json。不要把u50非匹配结果当纯学习增益。
- 远端4H200已无计算任务（重新检查）。监控仍可能在跑，曾观测训练全机约72–78%，累计20多分钟约50–60%；未满4小时，不作四小时合规声明。remote root /home/wangjiarui/artgym-newknife-20261005。用ssh33024，SFTP不可用，stdin cat/tar可用。runtime LD_LIBRARY_PATH 必须先 runtime/lib/python3.8/site-packages/torch/lib，再runtime/lib，不能继承全局Python3.12 torch。
- 三个必要泛化资产已固定 `NECESSARY-HELDOUTS-v1.json`：small-low/large-high/middle-variable。还没评估或用于训练；须先冻结候选，不能看结果后回调。

## 当前最重要的新机制

仅更正拇指朝向和小幅腕部换姿不足以稳定操作。纯法向压力曾前移39mm，但失去回收接触，否决。三支撑FK反推物体姿态误差大，也已否决，没有进入控制。不要再做压力方向/估计器调参网格。

`partial-front-v1` planning 得到约6mm、16°腕变化，拇指frontcos约0.5，原轨迹速度/碰撞证书通过；物理却把压力分到固定刀身，失败。其v2 preparation把旧关节预压改成基于新几何的0.3mm法向预压，仍失败，最多一轮8.3mm。保留失败。

随后发现更具体的结构问题：三个预期支撑接触x都是中心线同侧（-3.52,-3.56,-2.57mm），拇指x约0。法向静力平衡要求负支撑力，和实际刀体绕长轴滚转一致。SUPPORT-FOOTPRINT-DIAGNOSTIC.json。新方案把中指接触移到 +0.22×估计宽度，即+4.18mm；其他支撑的轴向位置保留。模型在0/17.5/35mm、假设拇指法向0.7/1.2N的6个条件均有正支撑解0.16–0.85N，不是实际力证据。

当前 preparation：`runs/newknife-20261005/preparation/crosswidth-support-v1`。

- 由 `plan_wuji_newknife_contact_pose --smooth --small-wrist --minimum-front-cosine .5 --middle-support-crosswidth-fraction .22 --sites 12 --initialize .../partial-front-v1 --base .../capfront-v2` 得到。
- 用 `prepare_wuji_newknife_joint_pose --continuous --lifted-operation --thumb-preload-normal-m .0003`。
- postlift 从旧capfront取刀，经12–14.2s已知电机路径进入新姿态，thumb/middle/pinky接触点IK跟踪，**不使用 --fixed-support-sites**，否则会把新中指目标改回旧位置。
- `postlift-transfer.json`通过：67帧、0自碰撞对、桌面间隙74mm、速度原限制内；点跟踪最大0.542mm。
- 将末端 hand_q 写入 `actual-transfer-motor-plan.json` 的 post_lift_close_q 后，`actual-transfer-stroke-audit.json`也通过，最大0.01615rad/frame<0.025。
- 原生入口支持 `--operation-prepared DIR`，会核验证书、去掉旧handover-calibration、加载postlift和新reference，保持原pickup计划与实际历史。新姿态不加载旧训练thumb权重，只使用S120支撑、thumb residual0。

**最新正在跑**：本地 `continuous/crosswidth-support-constant-v1`，完整36s视频。exec session6444（PID不能当实时事实，重新检查）。命令：

```bash
source runs/newknife-20261005/env.sh
python -m scripts.run_wuji_newknife --operation-prepared runs/newknife-20261005/preparation/crosswidth-support-v1 --scheduled-target-holds --output runs/newknife-20261005/continuous/crosswidth-support-constant-v1
```

先看其完整结果、真实拇指cap/body分力和中指接触的刀体横向位置，检验新支撑点是否真的建立；不要只凭静力图宣布成功。若改善再做variable和冻结必要泛化；若失败，应基于接触位置/力与执行器裕量定位，不盲目重复预压/压力网格。

## 交付尚待完成

- 选择并冻结最终具体方案；若未达成必须保留 false 标志和主要失效阶段，不能冒充功能demo。
- 全视频已有，每次raw continuous.mp4和hand-closeup.mp4均36秒。`compose_wuji_newknife_video.py`产生无剪切1080帧双视角+真实位移/制动模型标注，已验证一例。
- `run_wuji_newknife_selected.py`、package/restore脚本已写但 **FROZEN-CANDIDATE.json 尚未创建**，也未恢复验证。若最终用operation-prepared，记得给selected入口/包增加该目录字段。
- 两个可复用依赖包位于 runs/wrap-force-20261004/release/recovery-v43/，SHA在restore_wuji_traction.BASE。新overlay理论只需这两包，必须空目录实际跑一次确认。
- GitHub新分支/Release尚未发布。可适配publish_wuji_highload_snapshot.py，基线local4b71daac -> public87937c0862a22be1b6ed80b61990dbb0acb628ac；不要force。仓库 Jr-kelly/artgym。
- 私有 GOAL.private.md、原HTML和原照片绝不打包。package有过滤，仍需审计清单。

## 补充：尾侧跨宽支撑验证

前述crosswidth-middle已完整失败，第一轮4.267mm/第二轮2.795mm；实际中指x+2.53mm建立、拇指刀身力降到0.000265N，但index/pinky实际x约-8.99/-6.11mm仍使支撑三角形不能覆盖初始滑块。已固定下一机制：中指、小指均移到+0.22估计宽度，index保持负侧。planning/crosswidth-tail-support-v1。

preparation同名v1稠密路径失败：.2682rad/frame>原.025，未运行。诊断是preparer重新把jointplanner的约.5前向cos强拉到1.0，推到限位后跳解。增加 --preserve-authored-normal 保留插值规划法向，生成 preparation/crosswidth-tail-support-v2，最大点误差7.5nm，换握67帧通过，actual-transfer audit通过且峰值.006613rad/frame，未放宽限制。

远端4case脚本remote/crosswidth-tail-panel-v2.sh：constant/variable×clean/开发既有smallnoise，scheduledholds，no-video，使用同S120thumb0。输出development/crosswidth-tail-v2-*。确认启动后查日志。SSH必须用env LD_LIBRARY_PATH= /usr/bin/ssh，避免本地conda OpenSSL污染。4卡于13:12:52UTC核验idle，monitor1512仍在；PID需重新查。下一步读4case真实接触/行程，再决定录像/冻结；不能以静态证书声称成功。

## 补充：预压和可达换握修复

Tail v2四case与本地录像均失败（行程约0mm，cap接触约14–27%）。结果已全部同步，TAIL-SUPPORT-PANEL-v2.json，视频continuous/crosswidth-tail-constant-v2。新增diagnose_wuji_newknife_contacts.py可读取240Hz接触位置/法向分力，None frontcos表示非pad时按0处理。

找出旧support关节preload在新姿态指令6–8mm刀身穿透且横/轴向耦合。TAIL-COMMANDED-PRELOAD-FOOTPRINT.json。新增prepare_wuji_newknife_support_preload.py：先在初始估计底面建立contact，再按原actuatorKp和fixedlocalpointJacobian计算J^T F/Kp；力是模型proxy非实测。静力预检否决两指全+0.22W布局（需负中指力）；改小指中心线0，中指+0.22W，index原位。新的center-tail-support-v1规划/准备，法向proxy index.481/middle.405/pinky.853N，55g/COM0假设，thumb1.2N。所有位姿只用initialestimate。

center-tail-support-v1原postlift-transfer.json速度/碰撞通过，但pinky中段直线Cartesian路径碰joint2/4限制，tracking1.456mm超wrapper1mm，未执行。新增plan_wuji_postlift_regrasp --reachable-pinky-path，pinky目标改为合法joint插值的FK曲线，其余接触保留Cartesian，不放宽tracking/limits。目前生成postlift-reachable-transfer.json(exec64812)，完成后复制为新preparation版本的postlift-transfer.json并重做actual-transfer-stroke审计，不覆盖旧失败。旧auditexec43485针对被否决直线transfer，无需物理执行。

run_g2_robust_demo.py已修新刀report旧250damping描述为实际25000和新校准路径，metadata-only，现有物理数据不改。远端源码此修改尚未同步。下一次panel需同步源码/preps。

当前（精确时间见events.jsonl最后事件）center-tail-support-v2可达换握和actual-transfer audit均通过，maxstep.00672rad/frame、tracking5.2nm。remote4case constant/variable×learned/geometric支撑消融已启动，脚本remote/center-tail-panel-v2.sh，输出development/center-tail-v2-*。local完整双视角continuous/center-tail-constant-v2。13:21:19UTC启动核验；PID以实际进程/日志重新核验。旧证据目录完整保留。代码checkpoint c7768b2；新增所有脚本已py_compile。

## 最新：新抓姿训练正在运行（事件时间以journal为准）

center-tail-support-v2 +pressure120旧.1bound明显改善：constant本地首27.809/次17.979mm，端点27.849,19.126,37.105,30.680mm，capcontact1.0、原姿态/离桌/保持等均通过，仅行程/回收未达标。4remote profile×learned/geometric0对照也类似，CENTER-TAIL-SUPPORT-PANEL-v2.json。支撑残差关闭影响小。

pressureoffset.1在回程饱和，actualcapforce均值.808/.679N；开展.2bound ×current/Cartesian-normal的4case均失败，首轮32–33mm却丢第二轮或仅7mm。不选.2，不再扫pressure。全部结果CENTER-TAIL-PRESSURE-PANEL.json，remote数据已同步。

新prepare_wuji_newknife_training_scene.py复用原有batchpostlift/支撑waypoints，实现同actualpickup+12–14.2transfer+50history。batch/center-tail-config-v1。8env批量与native对照通过：取刀maxqdiff.0021rad、换握motor命令差.00115rad、操作slider最大差1.98mm，8/8无掉落、contactproxy1.0；CENTER-TAIL-BATCH-GATE.json。不是bitwise一致/独立验证。

远端新4training：constant/variable×thumb/motor，128env100update，每次819200transition，seed2026100522。actorhiddenfrozen，headLR3e-5，thumbscale.15/support.25，pressure120原.1bound，原actuator不变。thumb仅4head训练且support完整映射冻结；motor20head协同训练（新--motor-head-only），保留相同S120初始support，thumbhead清零。优化器梯度测试通过，隐藏层不变、support只在motor模式改变。脚本remote/train-center-tail.sh，输出train/center-tail-{profile}-{scope}-v1；100结束后同脚本自动evaluate_wuji_newknife_training_job两profile，输出development/faithful-center-tail-*。无需重复启动。

run_wuji_newknife现在允许opprepared与新checkpoint组合，但必须savedscene.operation_geometry_sha256完全匹配transfer/ref；旧grip权重仍拒绝。evaluate_wuji_newknife_training_job加--operation-prepared。源代码已同步remote。watcher在同一shell训练完成后运行，保留日志remote/train-center-tail-*.log。状态/完整性须核验。

仍未freeze最终候选、未消费3heldouts、未publish。当前最强可运行失败是center-tail-support-v2，不是早期旧抓姿训练权重。待当前四组全评估后按统一标准选取；不要重新扫旧失效路线。

## 继续后：动态支撑单项对照与共同几何适配

13:34:34UTC核验remote7371–7374训练shell与7441–7444训练进程仍活跃，update34–35，GPU54–83%。13:38左右update57已过半，仍高drop；不把拟合当独立验证。100结束后自动2profile完整复验保留。

新增prepare_wuji_newknife_stroke_support.py，由同初始几何/原Kp/已发35mm命令计算沿程正支撑载荷，forceproxy.405–.853N，reference最大变化.0929rad。基于first28/return19的实际接触/转动失效，不扫增益。prep center-tail-stroke-support-v1复制center-tail-support-v2，transfer不改、reference加support_offset_rad和support_reference_anchor。audit_g2_anchored_thumb_motor现在对含support_offset的路径同时检查全部支撑finger自碰撞/原jointlimits和support30Hz速度；exec31210正在结束。未通过前不执行。

g2_r800_policy.py支持显式reference里的support_reference_anchor，同时pressure转换改为使用实际knownsupportanchor而非始终initial（static默认不变，残差span仍.04）。不使用真实接触/刀体状态，真实actuator限制不改。新增sourcehash包括policy/reference/pressure/boundedresidual四模块。remote训练/已排队复验尚未同步该新policy，用原静态版本完整保留；dynamic对照在local当前代码运行。

prepare_wuji_newknife_case.py是统一initialestimate-only接续adapter，全程保留失败。common-recipe-nominal-v1失败：自动重优化wrist导致小指joint2 preload到-.37212，超原lower-.37，拒绝执行。新增fixed-wrist-from-initialize，沿用已认证nominalwrist仅适配contacts，common-recipe-nominal-v2正在最终审计(exec82680)。支持preload脚本现在明确落盘support-preload-rejected.json；原.005reserve不放宽。3heldouts仍未消费，最终候选仍未freeze。

同步视频center-tail-development-synchronized.mp4已完成1080帧36s、SHAa02d6e54f2456c55f7fbb9b291dbee6edeeeec539577c8f546e3c9df91ace8cb。build_wuji_newknife_delivery_report.py已实现待finalresults生成，未当成交付。

## 续接核验 13:49UTC

4新训练100与8faithful native全部完成，已同步本地train/、development/及remote日志；remote四卡0%、0MiB，无计算进程。动态支撑物理诊断失败，forward27.203/18.399mm，末回收22.656mm；实际60抽样对最小间隙.509mm但不能替代完整证书，保留diagnostic_not_countable。共同initialgeometry adapter nominal-v2两profile完整0pass，constant首27.605/次18.173，variable首27.643/次17.655。3heldouts仍未消费。下一步核验训练容量警告范围、全部paired排名，再freeze。

## 冻结与泛化启动

FINAL-DEVELOPMENT-RANKING.json根据声明规则选constant-motor100，SHA6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e；constant27.273/18.818，variable26.778/18.330mm，22/28checks、0fullpass。新128env训练出现foundLostAggregatePairsCapacity overflow，因此拟合有漏交互限制，8native单env日志无该警告，选型只用native。FROZEN-CANDIDATE.json已落盘，三个heldout分别session47071/21852/5674，完整36s constant录像26875，PID须核验。freeze后不再调权重/recipe/控制。
