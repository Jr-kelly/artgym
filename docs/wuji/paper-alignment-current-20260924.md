# 当前成功 Wuji teacher 与 ArtManip 论文的对齐审计

核验时间：2026-09-24 00:16 CST。结论：方法框架部分复用，当前成功分支不是严格论文复现；也尚无一套完整成功、最终验收通过的严格 Sharpa 论文复现实验。

本文替代 paper_alignment_audit.md 中“当前实验”的时效性，旧文保留为2026-09-21历史。本文不改训练配置或在途源码。

## 当前成功分支的逐项对照

|项目|论文 v1|当前 Wuji 三抓姿 teacher|结论|
|---|---|---|---|
|任务起点|功能抓姿，物体已在手中|预置功能抓姿|一致；均不含从桌面取刀|
|仿真与算法|Isaac Gym/PhysX、SAPG、512 LSTM、512/256/128 MLP、16维特权latent|复用主要仿真、算法和网络；20DoF使观测/动作维度变化|方法复用|
|时序|120 Hz仿真、30 Hz控制、40秒回合、到位切换|120/30 Hz；20秒；2/5秒外部指令|频率一致，任务协议不同|
|手与几何|22DoF Sharpa左手、Table6类别几何|20DoF Wuji右手、147×19×11mm、35g窄刀|用户要求的迁移差异|
|数据范围|30训练几何、5未见几何，自动功能抓姿集合|当前成功控制器仅1几何、3训练抓姿，第四抓姿保留为0成功|未对齐类别泛化范围；历史35资产不能计入当前成功模型覆盖|
|控制|全关节每步相对增量，alpha=.025rad|支撑16关节目标限制在初态±.04rad；拇指4关节每步增量±.025rad|显著动作空间改动，并非只替换手模型|
|动力学|Knife link0 40–200g、link1 10–20g，摩擦2–4，滑块阻尼700–1300；观测噪声.01|29/6g、摩擦3、阻尼.3固定；hand/object/task randomize均false，jointNoise=0；只在线随机化初态|未复现论文物性/观测随机化；.3未实物标定|
|奖励|Table7：近目标1、掉落−1、线/角速度惩罚权重50/2、接触1等；稳定性课程100→1100|训练近目标5、掉落−25、速度项−.5/−.02、接触0，加存活.1和绝对位姿代价；不同课程|显著工程改动，不是原论文奖励|
|训练预算|20000环境、horizon16、全局minibatch40000、LR2e−4自适应，约2B转移|当前续训5120环境、horizon32、minibatch32768、LR1e−5固定，从既有teacher续训100轮=16.384M新增转移/臂|不同；不能把新增预算当作总训练历史，也不能声称等同论文2B|
|精度/验收|训练5mm、评估10mm，每抓姿100次随机rollout；报告IC/GC/SR/CSC|20秒外部定时指令，每端点末.3秒<2mm，刀身全程<10mm/.25rad；小/宽扰动旧开发集|另一套指标；局部更严不意味着覆盖范围相同，成功率不可直接横比|
|student|冻结策略骨干，50帧TCN预测teacher latent，MSE，自身闭环采样|原形式已试验，效果不足；后续controller、DAgger、RGB等是额外迁移分支|当前最好RGB方案不能称原论文student原样复现|
|硬件|单独真实标定物选有效物理范围，再用独立真实测试对象|尚无Wuji实物参数/完整传感器动作链实机验证|未完成|

注意：评估config里的GoalDistance2=0.1及默认学习率不代表训练值。该权重的真实训练pipeline-status.json命令明确override GoalDistance2=5、LR=1e−5；评估关闭内部到位切换，独立从轨迹评分。本文按实际训练命令与评估配置分别取证。

## Sharpa 参考实验的边界

三组已实际建立：显式论文公式、上游实现、修复目标切换记账/掉落成功计分的上游对照。原手型、官方生成代码及30/5数据划分可复用，但三组不等价。

显式论文公式分支以及其物理诊断续跑发生NaN；删除空base、增加子步未解决，失败与CP保留，不能称成功复现。继续运行的主要参考为上游/修复对照，使用了上游的目标差平滑、位姿差分速度/裁剪、到位停留、10秒单阶段超时等，不等于论文公式。论文未明确的抓姿去重阈值、同时掉落/成功处理等仍是记录在案的实现假设。

截至00:10健康采样，修复组CP5550/6250，上游恢复组CP4350/6250；第二seed两臂500完成。周期评估10次/抓姿，论文式最终100次/抓姿与完整成功结论不可混用。该段为采样时状态，不代表未查验的后续完成。

用户要求的“论文参考实验”与“Wuji迁移实验”应保持独立身份。当前已运行两条研究线，但尚未完成一条与论文设定完整匹配并成功验收的参考基准。成功Wuji teacher与论文方法的关系应写为“基于ArtManip的Wuji迁移与改进”。

## 证据

- 论文：https://arxiv.org/html/2609.12498v1 ，§3.2–3.4、§4.1、附录C.3–C.6 / 表7–9；本地 research/paper.txt。
- 实际训练：runs/wuji_bridge3_reset2x_cp25_seed20261128_v1/pipeline-status.json。
- 实际评估：runs/wuji-goal/verification/reset-range-seed2-20260923-reset2x-cp100-small-2s-local-v1/config.yaml。
- 动作映射：isaacgymenvs/tasks/wuji_acquisition.py，命令调度：wuji_timed_acquisition.py / wuji_variable_timed_acquisition.py。
- 参考配置：isaacgymenvs/cfg/task/artmanip_paper_reference.yaml、isaacgymenvs/cfg/train/paperReferenceSAPG.yaml；参考差异：experiment_protocol.md。
- 失败与历次诊断：runs/wuji-goal/research/sharpa-success-and-wuji-student-gap-20260922.md。

## 本次巡检发现的续接事项

归一化/终止两配对均已训练完、44条件已重评分。归一化最终adaptive小294/299、宽256/282；strict终止最终小300/300、宽279/283，native最终小296/297、宽274/283（分母300、2s/5s）。均属已有开发集，第四仍0/32，严格终止效果不能由单seed最终差值推广。

终止终审v2的训练审计及分析完成，但打包因固定源码缺scripts.package_wuji_dagger_final导入失败，尚未上传。修复应使用新pin/新目录，保留失败，复用既有44轨迹无需再跑物理。

00:10八卡5分钟利用率21.76%、15分钟24.46%，已低利用率告警；4小时均值60.00%尚高于26%平台门槛。多数Wuji配对结束，需补充有用工作或调度剩余参考评估，不得宣称无告警。四卡4小时59.86%。原参考训练/CP调度保留。


00:18续接：补充四项有用的Sharpa匹配预算评估，upstream/corrected各CP3000/4000，五个未见几何全部有效抓姿各100次随机rollout。它只把该项重复数补齐，不能称完整论文公式复现或新的盲测。八卡GPU1/3/4/5，PID105768/105769/105770/105771；00:19已实查四个物理子进程105784/105781/105782/105783均在030运行，四卡GPU采样95%/97%/95%/96%。旧参考训练及CP监控保留。固定源码复用reset-normalizer-evaluations-eight-v3（archive SHA eed6f9f44a127d2ec19890bb24b942626b9f7a1aea544df5847458fb893fcf09），新增driver SHA ee4166ee86185c91ed58a5c9d42699776c4bdd3b32af99509ef6cdb51ad72f3c。配置、源checkpoint哈希、进程见 diagnostics/sharpa-matched100-20260924-v1/{spec,launch}.json。使用/tmp独占GPU租约，已加入五分钟健康注册；接下来收集四结果和逐项重算IC/GC/CSC，不把CPU包装故障误作训练失败。
