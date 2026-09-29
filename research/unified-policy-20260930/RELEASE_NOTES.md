# Wuji unified policy: bounded experiment completed, G2 not reached

同一权重尚不能稳定覆盖0/1/2+3。G0专家复核、G1扰动初始化的单专家序列克隆通过开发验证；两种统一初始化及两项受控修正均未过G2，已按停止规则结束训练。没有启动student或改用最终集调参。

冻结最佳失败候选的独立最终128初态严格成功数：

|协议|来源0|来源1|来源2|来源3|
|---|---:|---:|---:|---:|
|2秒|127/128|128/128|120/128|2/128|
|5秒|126/128|128/128|128/128|5/128|

源3刀身稳定115/128、118/128，也未达到95%门槛。统一候选为历史初始化BC100，SHA256 `3801eca359022e729510fef28f00d43b35af8561755f20a5f4be0206b6a07ab8`。这些是历史刀资产、已训练抓姿邻域的privileged teacher仿真结果，不代表真机或未见抓姿泛化。来源0/1相近，不能把四来源当四种独立基础构型。

- [完整报告、逐来源区间与阶段决策](https://github.com/Jr-kelly/artgym/blob/feat/wuji-unified-policy-20260930/research/unified-policy-20260930/README.md)
- [恢复与训练／评估命令](https://github.com/Jr-kelly/artgym/blob/feat/wuji-unified-policy-20260930/research/unified-policy-20260930/REPRODUCE.md)
- [2秒四来源同权重视频](https://github.com/Jr-kelly/artgym/releases/download/wuji-unified-policy-20260930-v1/wuji-unified-fixed2.mp4)
- [5秒四来源同权重视频](https://github.com/Jr-kelly/artgym/releases/download/wuji-unified-policy-20260930-v1/wuji-unified-fixed5.mp4)

视频为固定开发初态的单独RTX4090重仿真，两段均20秒600帧，清楚标明同权重teacher与每例成功失败，不能替代最终统计。H200相机初始化失败日志也保留。

归档包含两专家、所有实际保存的43个checkpoint及BC优化器/RNG、1024轨迹训练数据、开发与最终原始轨迹、资产/初态/配置和逐文件SHA。`wuji-unified-ASSETS.json`列出用途与下载地址；`wuji-unified-SHA256SUMS.txt`列出25项内容资产的哈希。恢复脚本拒绝覆盖不同文件。源3BC100→101实际恢复训练，并从归档解包核验；两个专家和最佳候选均可独立恢复。

记录占卡1.9083 GPU小时，加未计时早期预检的0.25 GPU小时保守额度为2.1583，最大同时2卡。GPU计算和自建监控已结束。整机采样约83.2分钟、均值23.08%，没有完整四小时覆盖，不能宣称通过四小时26%门槛。早停依据是失败分支，非预算耗尽。

下一步唯一优先：对源3的实际执行动作/目标关节监督做同起点同预算对照，先解决统一BC目标误差；这是后续建议，本轮未将其作为第三项修改执行。没有容量不足、单一归一化根因或论文创新宣称。旧Release和网站均保留。
