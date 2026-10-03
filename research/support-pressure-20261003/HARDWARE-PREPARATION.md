# 真机前的最小接口准备，尚未连接设备

本轮控制入口已完成离线检查：`scripts/replay_wuji_support_commands.py` 从合法关节测量、已发目标、时钟和初始估计复现 600 个操作目标。没有建立物理场景、实例化硬件 SDK 或下发真机动作。当前授权训练环境的已安装包中未发现 Wuji/G2 SDK。

官方旧版 Wuji Hand SDK 文档说明，关节位置读写使用弧度，手级批量数组为 5×4，实时控制器提供位置读取与目标设置。[官方 API](https://docs.wuji.tech/docs/en/wujihandpy/latest/api-reference/)。这仅确认公开接口，不代表当前设备固件、安装版本、关节零位/符号或数据新鲜度已验证。

仿真手顺序为 index、middle、pinky、ring、thumb，每指 joint1–joint4；不要直接将未知 SDK 的 5×4 数组展平给模型。实际 G2 右臂是 `idx61_arm_r_joint1` 至 `idx67_arm_r_joint7`；平台厂商与 G2 SDK 入口尚未确认，不能替换为其他机械臂接口。

官方将 `joint_effort` 描述为滤波后的电流空间驱动量，而非真实测量电流或指端力；实时控制器的 effort 读取也不等同于 Nm/N 传感器。本轮 actor 没有读取它。官方还区分出厂实际关节范围与 URDF 范围；本轮保持原 URDF 限位。[同一官方 API](https://docs.wuji.tech/docs/en/wujihandpy/latest/api-reference/)。

下一次真机所需具体输入：实际 SDK/固件版本和右手标识；20 个手关节、7 个臂关节的顺序、符号、零位及测量时间戳；有限位置目标接口与重力/执行器实现；桌缘刀位及手中刀/滑块的一次标定；实物滑块起動与槽位阻力曲线。触觉、物理电流或力矩反馈均未默认接通。只有核实接口与实际标定后，才考虑将额外信号用于后续控制。

无需本轮新建机器人栈。模型输入继续是匹配 teacher/normalizer 的 2076 维 R800 编码与选中残差维度；240 Hz 仿真电机实现、30 Hz 已发目标历史的真机对应关系仍待设备核实。
