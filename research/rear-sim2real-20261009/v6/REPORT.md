# v6 现场入口与连续会话

在当前分支接续v5，没有回退或重训。固定右臂与20D手目标仍走同一CoRobot point RPC，原策略/权重/参考/补偿不变。当前bundle-deploy-v11冻结504项依赖。

新增本项目operator入口及一次配置的启动脚本：等待开始时不连运动端；模式按真实HTTP合同配置/开始remote_env；空手实际姿态有界到位只执行一次；命名确认门防重复；同一连接暂停保持最近RPC接受目标；受载外部reset拒绝；正常卸载后结束流，绝不宣称失能。Forge入口直接运行完整现有控制器。实际PolicyServer infer/reset协议无执行回执，故沿用既有controller/remote_env，而非状态server或虚假infer执行成功。

新增26项针对性检查通过：21项真实已安装客户端HTTP/RPC与启动/模式/初始化/会话保护，395周期p95 4.771ms、max8.083ms、零>33ms；另5项最终launcher/路径/504pin/4帧空手点动作/只读采集。均为明确离线协议端点，不是现场GDT或真机。首次验证汇总脚本字段错误与原日志保留，后续只重查本轮新增生命周期。

既有20合同、380帧对齐、1174周期完整会话及条件10ms过渡的32.209mm/1.033s物理结果复用，未重跑物理或矩阵。控制合同、所有数值参数/权重不变；10ms没有改写成现场参数。

现场FIRST-FIELD-SESSION.md完整指南与私有扩展/实际包单独交付；旧USB和状态server指令已移到history，当前指令不再夹带历史入口。指南明确host/container、INFER_INIT_POSITION取消、只读、空手到位、摆刀、响应、probe、卸载复位30mm、新历史fullpush与退出。

仍需具体现场组件对right_effector/hand_joint_states/PointAction的真实名字/单位/编码器来源、绝对语义/后处理/频率/过期停止，及零位/安装/固定体/时钟对应。工具一次只读采集版本、状态和时序并保存失败证据。缺项没有通过删除检查解决。hardware_deployment_complete=false、real_robot_ran=false。
