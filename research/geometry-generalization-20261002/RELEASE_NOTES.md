# Wuji knife geometry generalization, 2026-10-02

冻结 teacher / SA51200 在受控刀柄尺寸变化中的配对评测，以及一次未通过续训前提的 learner-state 特权 latent 诊断。保留旧模型与所有旧 Release。本轮没有新 optimizer 更新、没有模型提升声明、没有机器人实验。

完成13条件78个筛查协议运行、9个关键条件54个独立确认协议运行；独立最终评测13条件78协议，5951个静态有效初态复用为35706条协议episode记录。SA在已覆盖来源上的几何等权F成功率98.55%、全程持握83.24%；W120来源3最终开合50/102、持握2/102，teacher102/102、95/102。S2/S5严格成功率69.20%/63.78%，不同于功能开合。完整结果及实际预算见分支 FINAL_REPORT.md。单轴离散尺寸为 L117.6–176.4 / W15.2–22.8 / T6.4–9.6 mm，其余轴固定；质量和有效惯量固定，滑块机构与控制保持基线。静态有效初态下的条件操作能力和抓姿覆盖分别报告。

独立确认的 W120 来源3：teacher 完整开合64/64、40秒持握55/64，SA为33/64、2/64。两秒 SA 前缀之后换 teacher latent，可提高持握到25/64，却使开合降到26/64；没有满足事先登记的蒸馏训练条件。长度来源3存在适配覆盖缺口，部分来源2的 SA 比 teacher 更稳。下一轮优先局部功能抓姿适配修复，再以新开发数据验证假设。

数据包：父模型含 Adam/RNG；受控资产包含13个新URDF、缓存、接触IK初态和明确拆分的扰动数组；筛查/每几何确认/特权诊断/每几何最终包保留原始动作、目标、slider、body与终止轨迹。静态/视频/恢复/作业包保留选中行、失效记录与日志；源码pins包按每个实际不可变运行版本提供 content-addressed blobs。

视频包含 baseline、L80、L110、W120 的同初态 teacher/student 并排及预览图。它们是单独 RTX4090 摄像重新仿真；失败列保留，不代替 H200 统计。F 到位调度读取仿真 slider 真值。所有结论依赖仿真、初始化标定与已知几何，不能作为 sim2real 证据。

离线 reset/step 的 CPU 原player逻辑回放通过；实际 H200 输入在 CPU 回放未过跨设备一致性容差。负结果、精确网络输入诊断及部署边界全部保留。

恢复：plain clone 本分支（无需 legacy SSH submodules），用 scripts.restore_wuji_unified 解包父模型/受控资产，按 REPRODUCE.md 在兼容 IsaacGym runtime 中运行。各数据包GitHub digest已核对；发布后的匿名关键包下载/恢复、完整视频解码及实际公开源码命令核验记录保存在该研究目录的 public-verification.json/public-command-verification.json。这些交付核验在科学结果提交后写入分支，不能冒充新增独立能力样本。

科学结果、图表和复现说明：[本轮研究目录](https://github.com/Jr-kelly/artgym/tree/feat/wuji-geometry-generalization-20261002/research/geometry-generalization-20261002)。
