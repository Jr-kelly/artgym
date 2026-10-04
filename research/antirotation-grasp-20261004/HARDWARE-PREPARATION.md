# 本轮离线接口准备，未执行真机动作

沿用前轮确认的2076维R800、匹配teacher/normalizer与154维750桥；本轮没有发现新SDK或实物力—位置数据。手关节按名称为index、middle、pinky、ring、thumb，每指joint1–joint4，G2右臂为idx61_arm_r_joint1至idx67_arm_r_joint7。未知SDK的5×4数组不得直接展平；SDK effort不作为Nm/N传感器。

`scripts/g2_r800_policy.py::prewarm`在50帧真实关节/已发动作历史和一次估计接管建立后，隔离控制状态进行完整推理/参考/目标计算，丢弃所有预热目标，恢复RNN、已发目标、动作记忆和参考状态，再开始实际控制。没有伪造或覆盖测量历史。`scripts/replay_wuji_support_commands.py --prewarm-iterations 8`已复用前轮真实合法记录重放600帧；预热后首帧2.72 ms，中位2.62 ms，95分位3.37 ms，最大5.33 ms，无超过33.3 ms的帧。仅4090离线推理时序，不含SDK传输、电机或测量延迟，也不保证真机实时性。证据：`runs/antirotation-grasp-20261004/offline-prewarm-v2/`。仅预热神经网络的首试仍有约96 ms首帧，保留为失败记录。

实际接入缺项仍为：G2/Wuji SDK/固件版本及右手标识；27关节名称、符号、零位、单位、带时间戳测量；有限位置目标接口及执行器/重力响应；初始桌缘刀位与手中刀/滑块估计标定；双向实物起动/沿程阻力、有效行程与完全收起端点。未建立假SDK适配器或自动连接设备。新抓姿已有冻结750实际连续仿真 V17，但必要泛化仍未解决；此离线桥检查与仿真成功均不代表真机已验证。

实物测量步骤与CSV见`REAL-MEASUREMENT.md`，小型入口`scripts/fit_wuji_passive_resistance.py`输出分方向被动容量profile和原始点/模型图；当前只有明确标注的合成解析例。可显式通过`run_g2_robust_demo --measured-resistance-profile profile.json --resistance-integration solver-brake`将未来数据接入物理阻力。容量不输入actor，未测范围拒绝外推。真实卡槽阻力上限没有据现有仿真容量编造。


2026-10-04新增抓姿的 V17 合法输入回放：当前控制器600帧指令最大差9.54e-7 rad；并行训练时推理中位14.55 ms、95分位24.61 ms、最大28.98 ms。证据`runs/antirotation-grasp-20261004/offline-v17-replay-v1/replayed-current-source-v2/`。此前速度数字来自不同记录/负载条件，不能移用作本轮真机实时性承诺。

新的5秒接管控制器属实验分支：必须传入一次已知桌面配置、带噪声初始尺寸估计和取刀动作计划，用实测机械臂关节FK转换初始刀/滑块位姿；闭合、提升、支撑交接参考只由计划与已知时钟生成。16秒时仅调整软件操作参考，不重置物理、关节历史或RNN。离线入口新增`--motor-prefix-plan`，禁止以未来记录目标代替动作参考。该分支尚待冻结权重的原生行为与回放验证；缺少SDK时没有自动下发路径。
