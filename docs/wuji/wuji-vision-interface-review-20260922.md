# Wuji 官方视觉部署接口复核

研究范围：固定官方 `wuji-technology/wuji-mjlab` 提交 `9410a3ac9caf57ac0b8c74c0a5a63f2b466c3003` 的源码阅读，未接相机、未控制硬件，也未训练视觉模型。原始七文件及 SHA256 保存于 `../research/wuji-vision-pinned-20260922/manifest.json`。外置相机是否符合用户最终装置约束仍待回复；现有纯关节反馈实验继续。

官方 `deploy/reorient/README_zh.md` 明确部署不是纯本体感觉：关节状态来自 Wuji driver，方块位姿来自 ArUco 方块标签和手腕 AprilTag，经 ZMQ 送入策略。可复用相机内参/ROI处理、手腕坐标标定、PnP与四元数连续性处理、最新消息接收、关节驱动和策略动作配置导出。它没有美工刀滑块的关节测量，方块预训练策略不能用于美工刀。

本次读取的具体限制：

- `config/camera.yaml` 配置90 Hz采集、5000微秒曝光、1280×1024传感器和616×504快速ROI。它是配置值，不能当作实测帧率、精度或端到端延迟保证。
- `cube_world_observer.py:1075` 在发布时调用 `time.time()` 填充时间戳，没有用该字段记录曝光时间。仅按这个时间戳计算消息年龄，会漏掉采集和视觉计算耗时。
- `zmq_bridge.py` 的 `CubeReceiver` 使用接收队列长度1和 `CONFLATE` 保留最新消息，可避免消息队列积压；这不等于观测足够新。
- `CubeReceiver.get_pose()` 的 `valid` 条件是收到过数据且 `world_fixed` 为真；`latest()` 缓存最后有效位姿。这两个接口没有自行检查消息时间戳/帧号是否过期。发布器没有新检测时不发布新的方块位姿，接收端仍可保留旧值。此结论限于所读接口，不断言整个官方应用所有调用点均无保护。
- 接收器把视觉的xyzw四元数转换成MuJoCo的wxyz；我们的IsaacGym获取坐标约定不同，不能原样拼进teacher输入。需显式标定手腕标签→手基座和手基座→当前训练获取坐标系，分别核对刀身与滑块。

如果后续允许相机，可先独立验证“刀身位姿+滑块一维行程”的测量；刀身与运动部件必须分别被观测，单个刀身标签不包含滑块位移。窄刀19mm宽、拇指遮挡滑块、刀片收回后的可见性决定标签或轮廓方案，不能直接缩放54mm方块标签布置。标记/附件若影响接触、质量和惯量，也必须进入数字孪生并重新评估。

本任务已有冻结teacher反馈干预显示：单独33ms延迟仍接近无延迟，100ms显著降低成功率；单独1mm滑块恒定偏差相对温和。它们是单因素仿真结果，不能直接当作组合视觉误差、丢帧和真机时延的允许上限。应记录曝光/采集、估计完成、策略消费和动作发出时间，先在仿真中对实测误差与延迟分布作闭环验证，再进行硬件测试。相机可用也不等于目标已完成。

来源：

- https://github.com/wuji-technology/wuji-mjlab/blob/9410a3ac9caf57ac0b8c74c0a5a63f2b466c3003/deploy/reorient/README_zh.md
- https://github.com/wuji-technology/wuji-mjlab/blob/9410a3ac9caf57ac0b8c74c0a5a63f2b466c3003/deploy/reorient/scripts/cube_world_observer.py
- https://github.com/wuji-technology/wuji-mjlab/blob/9410a3ac9caf57ac0b8c74c0a5a63f2b466c3003/deploy/reorient/lib/zmq_bridge.py
- https://arxiv.org/html/2609.12498v1 ，A.2 对部分可观测性和视觉/触觉的讨论。
