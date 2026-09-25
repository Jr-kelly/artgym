# Wuji teacher + student：基本美工刀滑块开合验证

范围依照用户最新澄清：沿用ArtGym teacher→student流程，从预置功能抓姿开始完成刀具滑块伸出/收回。桌面取刀、真机标定和广泛未见物体泛化留到后续。

复用已训练的冻结teacher CP25和原纯latent MSE student最终update1000；本轮未重新训练或修改模型，而是补齐与目标对应的独立物理验证和可复现交付。Student的16,384,000个正式训练转移全部由自己驱动，teacher接管0，actor/normalizer/teacher encoder冻结审计通过。

冻结后生成三训练功能抓姿各100新扰动初态，全部保留、不按结果筛选。参数化刀身+被动滑块，147×19×11mm、35g、同1把刀。20自由度Wuji、30Hz控制/120Hz物理；没有刀刃切割接触模型。

|策略|时长|至少3轮完整开合|全程自然存活|平均循环|
|---|---:|---:|---:|---:|
|teacher|20s|298/300|191/300|15.37|
|teacher|60s|298/300|143/300|37.20|
|student|20s|298/300|294/300|17.00|
|student|60s|298/300|240/300|42.95|

上表采用10mm到位判定、到位即刻发下一开合命令。高层评估器使用仿真到位检测；student的动作输入不含当前物体真值。

另做完全外部固定2秒/5秒换向，两种20秒测试的student全部端点末0.3秒保持<10mm为293/300、297/300，自然存活296/300、297/300；对应原2mm+全程刀身严格标准仍只有126/300、184/300。它们是不同评估问题，不替换或隐去旧失败。

结论：预置抓姿下的teacher+student基本滑块开合已有独立物理验证。60秒连续快速操作仍有后期掉落（student240/300存活），严格2mm精度/刀身稳定尚未解决。这些高要求单列，不再作为用户本次基本功能Goal的前置条件。

方法沿用ArtGym的特权teacher、50帧本体感觉latent蒸馏和冻结actor路线；手型对应的执行器/动作映射、物性、奖励与预算有迁移差异，不能称参数逐项完全复现。没有新物体/第四抓姿或真机成功声明。

所有视频无文字，完整20秒保留，包括后段不稳定；三个显示初态固定为新集合行0/100/200，两个完整相机视角均发布。视频重仿真不加入300个独立试验分母。

复现入口：`scripts.collect_wuji_core_evaluation`；打包：`scripts.package_wuji_core_task`；发布校验：`scripts.publish_wuji_core_task`。最终Release清单见`diagnostics/release-core-teacher-student-20260924-verified.json`（完成上传后生成）。

teacher SHA256: `4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac`
student SHA256: `022ad8c7b3af18e25681fcd4073c1b48858621470293036df0311c488068e0f5`
numeric source SHA256: `bdefce16af75fb0a7d25116b0b2e07f78b543b7bc2239980e0482820d341667c`
initial-state SHA256: `4676b03d807a6ae8f40e112b2f900161030f89f176678910d679e0694546a239`
