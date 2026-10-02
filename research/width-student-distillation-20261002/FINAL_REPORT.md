# Wuji 跨宽度 student 蒸馏：当前交付与硬阻塞

本轮尚未得到训练对照结论。已实际完成多资产实现、全新数据准备、静态验收和真实 reset/step 检查；提供的 SSH 端点此前两次连接超时，本次2026-10-02T07:11:48Z重连仍在认证前超时，H200 数量、任务和新增远程消耗仍未核实。C/G 正式优化均为 **0 次**，没有可参与正式模型选择的新策略 checkpoint，也没有 P/C/G 操作成功率、未见几何策略结果或训练后视频。连接失败不能解释为几何蒸馏无效。新 Goal 保持未完成，旧最终集和已有 Release 未改动。

从已发布研究头8968914接续，GitHub分支已重新读取并一致。父 teacher/student 文件 SHA 与附件一致；实际 student Adam 步数51200，交互52,428,800，lr0.0003及原loss/冻结合同经只读CPU检查通过。

C/G 使用同一学生/冻结actor；固定128/64/64环境逻辑组逐槽位匹配来源：组0各32，组1/2为来源0/1/3的22/21/21。G后两组分别W110/W120，C均baseline。来源2只从baseline训练，在每个宽度评测中保留。采样metadata未进入policy，恢复后只初始化一次新优化随机流；absolute --updates54400对应每臂新增3200Adam更新/3,276,800transitions。原20秒训练horizon、控制、Adam moments、损失及teacher warmup绝对计数保留。

已生成11,776条新尝试初态，登记train/dev/confirm/final不同种子与W115、W115+T110。三个已见几何的dev均得到32有效状态/来源；训练允许的10个geometry/source池均256个有效状态，共2560个不同训练状态。C重复引用baseline池不计新增独立状态。旧final数组未读取，单几何各新split的逐行SHA无重复。

静态结果见[STATIC_COVERAGE.csv](STATIC_COVERAGE.csv)：它们来自单独RTX4090仿真，只验证2秒无policy持握与原穿透代理/关节/漂移/旋转/局部thumb IK阈值；不能替代H200策略统计，也不是新的抓姿类别泛化证明。两个未见几何只做预登记结构/静态检查，final policy仍关闭。C/G多资产实际实例、两bbox、hand_base缓存及2076维SC输入验证通过。

保留失败：同一Python进程销毁C仿真后创建G时发生原生signal11；C/G改为独立进程后各通过。归因范围是此次双仿真进程生命周期，未证明所有IsaacGym重建都不可行。一次CPU归档收据相对路径错误在已完成包上修复，未重算或覆盖原包。

尚须执行：同H200后端零变化路径/teacher latent与incomingRNN一致性；fresh-dev少量teacher从reset；两臂可丢弃副本真实更新和完整训练吞吐；正式匹配窗口、开发判断、冻结及独立final和P/C/G/teacher视频。有限队列及原子checkpoint/readySHA/执行PID/超时收据已实现，最多8个独立单GPU任务；实际空闲设备数决定并行度，无DDP或env扩容。预登记队列尚无一次H200执行，首对及最终交付ETA待真实吞吐后报告。

前次交付已完成11个GPU准备作业（含失败），实际新增 **0.03945493 GPUh**，峰值1张RTX4090；H200使用0张。账本此前40.43593222，当前已知累计 **40.47538715 GPUh**，预计剩余 **23.52461285 GPUh**，保留6GPUh。远程可能新增的消耗未知，恢复接入后须先对账；不能把此预计剩余当作远程已核实事实。准备阶段截至本报告墙钟33.44分钟，主要外部等待是SSH不可达；不以8倍卡数声称加速。没有远程四小时利用率证据，也没有填空耗作业。

下一步唯一优先：恢复已提供端点的可用连接，按HANDOFF接续H200预检和第一配对窗口；不要重新生成已验收数据、重新初始化Adam或重跑旧final。源码/资产、静态准备、待执行训练、冻结独立验证、渲染视频和真机结果分开；没有机器人操作或sim2real结论。

准备交付：[独立分支](https://github.com/Jr-kelly/artgym/tree/feat/wuji-width-student-distillation-20261002)、[准备Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-width-student-distillation-20261002-preparation-v1)。两个资产服务器SHA与本地一致，主准备包161文件恢复通过；此版本明确不含新训练策略或训练结论。

## 第二次接续：实际实现验证，正式研究仍被连接阻塞

已复用原数据和父权重，新增6个有限RTX4090作业。零变化比较采用256个相同新训练初态、8个真实控制步；原baseline路径与多资产C路径的public input、SC输入、action、target、incoming/after RNN最大差值均为0，见[ZERO_CHANGE_PATH_AUDIT.json](ZERO_CHANGE_PATH_AUDIT.json)。同输入二次forward与实时控制相同。此结果仅覆盖该设备上的短路径数值一致性，不认证H200，不证明操作能力。

C/G各从未改动SA51200进行16次真实on-policy teacher标注、物理步进、loss/backward/Adam，再各从自己的51216原子checkpoint恢复1次更新。合计 **34次可丢弃实际更新、34,816 transitions**，正式更新仍 **0**。仅student encoder发生变化，冻结actor/normalizer/teacher哈希保持父模型一致，warmup fraction为0，Adam实际步数/交互计数/自身恢复通过；目标映射误差最大2.3841858e-7 rad。见[DISPOSABLE_OPTIMIZER_AUDIT.json](DISPOSABLE_OPTIMIZER_AUDIT.json)。四个checkpoint明确禁止参与正式训练起点、模型选择或能力结论。两个16步完整训练循环分别8.6156s/8.6325s，只是RTX预检测量，不能推算H200首对ETA。

此接续新增 0.01372562 GPUh；本轮全部准备/预检新增 **0.05318055 GPUh**，原累计已知 **40.48911276 GPUh**，64GPUh预算预计剩余 **23.51088724 GPUh**（其中保留6GPUh）。远程额外消耗仍未知，恢复连接后必须先对账。所有新增GPU作业均已结束，未继续本地训练填充利用率。最新18任务P/teacher开发队列v5仅登记、未执行；旧队列保留作未执行历史。

后续从原SA51200重载，先在同H200完成尚缺的预检、teacher行为和吞吐注册，再进入匹配窗口。既有成功链路、冻结结果、旧Release和用户修改均保留。训练/独立final/对照视频仍未完成，当前证据不支持跨宽度蒸馏成功或失败判断。

新增两份预检资产已加入同一准备Release，服务器SHA一致，71文件证据包恢复通过；旧资产保留，现共四份资产。交付前再次SSH重连仍超时，见connection-recheck-turn2-after-delivery.json。
