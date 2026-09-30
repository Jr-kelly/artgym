同一套 Eagg6100 特权 teacher 权重在固定仿真刀、已训练抓姿邻域上通过来源0/1/2/3的严格保持门槛；固定第二优化种子也通过本轮新最终128例验证。推理不按来源切换专家或权重。

|最终指标，每来源128例|源0|源1|源2|源3|
|---|---:|---:|---:|---:|
|S2，20秒完整严格成功|128|127|127|111|
|S5，20秒完整严格成功|123|128|128|110|
|F，40秒内至少一轮伸出和收回|128|128|128|128|
|F，全40秒刀身稳定|127|115|110|125|

S含绝对严格≥80%、刀身≥95%，以及相对同批负责专家下降≤10/3个百分点。源3 S5相对门槛仅余0.625点。F循环成功不等于全程稳定；Wilson区间与全部18模型结果见[完整报告](https://github.com/Jr-kelly/artgym/blob/feat/wuji-artmanip-recovery-20260930/research/artmanip-recovery-20260930/README.md)及[最终表](https://github.com/Jr-kelly/artgym/blob/feat/wuji-artmanip-recovery-20260930/research/artmanip-recovery-20260930/FINAL.md)。

直接联合RL完成327,680,000交互/144,000Adam，最终F为[124,127,128,128]/128，严格S与刀身门槛未完成；这是预算受限基线，不是收敛或方法无效的结论。同预算M/E、执行动作延长、数据聚合/旧数据重放和保持目标对照均保留。聚合6500固定末点未过源3 S5相对专家条件；主候选6100在最终集打开前已选定。第二种子的64例开发边缘失败也保留，未放宽标准。

54个模型/协议组合、27,648回合全部从实际恢复的原始归档独立复算，唯一性、权重/初态/源码/协议覆盖检查通过。全部权重内容可恢复，保留真实Adam/RNG、原始轨迹、逐回合CSV及固定失败演示。三段MP4均为四来源同权重、600帧/20秒独立本地重仿真；源3失败明确标红，不替代最终统计。

- 快速开始：`recovery-primary-candidate-Eagg6100.tar.gz`（约69MB），归档SHA256 `3fa51b91d03e7cb795f9b8a27bd3d7b0fd81233e0c5137ea2753901025cf2d31`。
- 主权重SHA256：`2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8`。
- 完整最终复算：`recovery-final-weights`、18个每模型归档、`recovery-final-batch-records`及`recovery-final-analysis`；命令见[REPRODUCE](https://github.com/Jr-kelly/artgym/blob/feat/wuji-artmanip-recovery-20260930/research/artmanip-recovery-20260930/REPRODUCE.md)。
- 三段直接视频：`recovery-teacher-S2.mp4`、`recovery-teacher-S5.mp4`、`recovery-teacher-S5-failure.mp4`。
- 资源：占卡22.4177GPUh，含保守预检余量22.4677<24，最多2卡；所有自建GPU作业与监控已退出。远端末4h整机30.51%，达到26%但未达40%目标。

本轮只完成特权teacher；没有student、未见抓姿、形状泛化、自主取刀或真机结果。下一轮只优先核查可用观测后的统一teacher→student蒸馏，并使用新登记验证集。历史分支、Release和网站保留。86资产服务器哈希、主候选和3视频的匿名下载哈希均通过；下载后实际恢复CPU模型/Adam/RNG并解码600帧/20秒视频。[公网验证回执](https://github.com/Jr-kelly/artgym/blob/feat/wuji-artmanip-recovery-20260930/research/artmanip-recovery-20260930/public-verification.json)与[最终交付](https://github.com/Jr-kelly/artgym/blob/feat/wuji-artmanip-recovery-20260930/research/artmanip-recovery-20260930/final-delivery.json)在科学标签之后追加提交。
