# Wuji 多抓姿 × 支撑动作范围（执行中）

尚未得到正式训练或冻结评估结论。旧刀 URDF SHA256 `5229c66b183cc6da04190bf2d6cfbd035fadd227340dc8f26602b207171b461c`，原 teacher SHA256 `4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac`。

独立分支 `feat/wuji-multigrasp-2x2-20260928`。工作目录 `/data/research/artgym-experiments-20260921/multigrasp-20260928`；远端 `/home/wangjiarui/artgym-multigrasp-20260928`。开始 2026-09-28 14:53:52 UTC，截止次日 02:53:52 UTC，至少最后一小时用于评估交付。

| 组 | 训练记录 | supportActionSpan | seed | 正式预算 |
|---|---:|---:|---:|---:|
| A | 原 3 | .04 | 2026092801 | 1000 × 5120 × 32 |
| B | 16（包含原 3） | .04 | 2026092801 | 同 A |
| C | 原 3 | .20 | 2026092801 | 同 A |
| D | 同 B | .20 | 2026092801 | 同 A |

四组随机初始化；初始所有模型张量 digest 必须一致，记录见 receipts。旧权重只作附加参考，不参与初始化。动作中心逐回合为 init_targets；拇指仍按 prev_targets 增量 .025 rad/step。沿用 bridge3 的原刀坐标转换和四元数半球约定；观测137维，20动作，30Hz控制。训练均在线 ±.5mm/axis、±.01rad/joint、±.5°旋转向量分量扰动，noise ramp=0；奖励/网络/物性/终止/curriculum 同配置，仅训练池路径和 span 不同。

静态预检24记录全部存活20秒，最大刀身漂移2.36mm、转动.155rad，未推动滑块。24记录含两个逐位重复；保留原三个训练记录中另有一对近邻（2.23mm、2.03°、关节RMS .0595rad）。按5mm/.05rad/5°关节RMS合取去重，原3属于2个构型簇，16训练记录属于15个簇。重复和近邻不跨训练/测试。不能将16记录称为16个严格独立构型。

训练与开发分组在运行前冻结于 `data/manifest.json`。历史已查看 functional20 其余来源仅作为历史保留诊断，不称盲测。新测试 seed2026092803 从官方功能抓姿生成入口产生，最多2700秒生成与1800秒第一物理筛选；后续保持门槛固定，与策略结果无关。

开发集：16训练记录各8个新扰动，CP250/500/750/1000按2/5秒固定时钟严格成功率等权选择，平局取较晚CP；不使用新测试调参或选权重。严格协议：20秒完整开合；各2/5秒指令末.3秒连续滑块误差<2mm、整段刀身平移<10mm/转动<.25rad且自然存活。继承历史严格小于门槛，不在看结果后放宽。额外现有协议：10mm到位立即反向，20秒连续完整开合计数、至少3轮和alive_full。两种协议各自运行，不能互换成功率。

当前吞吐预检约每轮10.6秒，163840交互；四卡并行各卡内串行，避免同卡训练/生成/评估竞争。GPU历史为本机采样，非平台四小时计费口径。每个job都有14400秒上限、命令、PID、状态和GPU采样；监控只镜像证据不重启任务。全部旧任务/视频/模型保留。无student训练、无机器人动作、无新刀物性替换。

## 入口

训练：`python -m scripts.train_wuji_multigrasp task=wuji_multigrasp hand=wuji_paper_official_actuator object=knife_wuji_bridge3_20260922 train=wujiAcquisitionSAPG num_envs=5120 experiment=NEW_NAME max_iterations=1000 headless=True graphics_device_id=-1 pipeline=gpu seed=2026092801 train.params.config.expl_coef_block_size=1024 train.params.config.minibatch_size=32768 task.env.trainingStates=research/multigrasp-20260928/data/small.npy task.env.supportActionSpan=.04`。完整实际命令以 receipts 中运行记录为准，补充保存频率、奖励固定值等选项。

固定时钟：`python -m scripts.audit_wuji_multigrasp --checkpoint CHECKPOINT --task wuji_multigrasp --hand wuji_paper_official_actuator --object knife_wuji_bridge3_20260922 --initial-states STATES --span .04 --stage-seconds 2 --output NEW_OUTPUT`。`--static`替换为初始关节目标保持。

到位换向：`python -m scripts.audit_wuji_multigrasp_arrival --checkpoint CHECKPOINT --task wuji_multigrasp --hand wuji_paper_official_actuator --object knife_wuji_bridge3_20260922 --initial-states STATES --span .04 --total-seconds 20 --output NEW_OUTPUT`。

全部运行环境使用 `scripts.monitor_wuji_checkpoints.runtime_environment`，IsaacGym先于torch，独占GPU租约。数据预置与复现整理在收尾时完善。结果、视频和下一步尚待真实实验，不预判两因素作用。

## 15:17 UTC 更新

四组均已正式运行，随机初始化全张量哈希完全相同。`configs/audit.json` 对实际命令重新合成四份完整配置，除运行名称外只有训练池、span这两个预定因素不同。运行时动作映射与训练池采样20800交互核验通过。

旧冻结teacher在24候选记录上2秒指令：18/24存活，9/24至少开合一轮，5/24通过全部严格端点+刀身稳定；这5条正是原3条及2重复，去逐位重复后3/22。额外4条能开合一轮但不满足全程严格要求，不能称所有新抓姿都无法操作。这是历史候选诊断，本机4090结果，正式四组另在H100使用相同评估配置比较。

新seed2803：1000候选、24第一阶段有效、20秒21/24存活；固定姿态+拇指行程检查0合格，不虚构新盲测分母。已限量排队追加seed2805的3000候选，A训练结束后GPU0先生成再开发评估；其余各卡训练完成后开发评估。

接触数组顺序为thumb/index/middle/ring/pinky，关节顺序为index/middle/ring/pinky/thumb。初版离线接触标签曾颠倒，标为`*.invalid-contact-order.json`保留，修正文件`*-contact-order-v2.json`有效；物理轨迹和成功指标未改。

一键重现某臂：`python -m scripts.reproduce_wuji_multigrasp --arm A --gpu 0 --name NEW_UNIQUE_RUN`。复现脚本给6小时监控上限，不改变1000轮交互预算；当前首轮实际已启动监控上限4小时，接手须根据吞吐核查是否足够（尤其more/.20），超时不得当方法失败。

## 15:25 UTC 更新

四组训练PID重新实查存活。最近20epoch平均A10.70/B12.94/C11.75/D14.22秒；D的4小时监控上限接近预计总时长，需要续接时检查，不能让基础设施超时造成不等预算。

旧teacher5秒固定时钟结果：19/24alive、9/24完整第一轮、5/24全部严格，严格成功仍仅原3记录及2重复。完整视频已生成于 `videos/reference-three-grasps-policy.mp4`，manifest写明选取规则、物体/权重/输入及同一脚本实际重仿真结果；600帧、20秒、30fps。3-env视频实际行0成功、行3推不动、行5旋转过大；行5没有复现24-env数值诊断中的掉落，不能称精确重放。同一个基础初态的不同并行批量也存在仿真差异，正式四组在相同批量/设备/协议比较。

新测试seed2803的物理门禁联合结果固定为0合格，见data/fresh2803-frozen/manifest.json；保留失败，不运行空分母评估。第二批3000候选仍在A训练之后的队列中。冻结最终四组+旧参考统一评估入口 `scripts/evaluate_wuji_multigrasp_frozen.py` 已实现，尚未执行（等待训练/开发选定权重与合格新测试）。
