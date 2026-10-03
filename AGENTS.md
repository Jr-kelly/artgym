# Wuji 承托与持续按压当前轮

先读 WUJI_GOAL_HANDOFF.md 和 research/support-pressure-20261003/GOAL.md。
实际实验副本为 /data/research/artgym-experiments-20260921/support-pressure-20261003。
本轮最新用户附件明确取消 GPU 小时上限与利用率指标，覆盖旧轮26/27/40%要求。仅运行有用工作，禁止子代理、填充负载和自动真机动作，保留ToDesk及其他用户进程。
每项实验开始/结束、配置/机器/进程变更、结论与失败均更新当前续接文档和 /data/research/artgym-experiments-20260921/runs/wuji-goal/journal/events.jsonl；证据含时间、路径、配置、必要权重哈希和下一步。
旧冻结结果与旧Release不变；runs旧目录为只读使用的基线引用，新输出只能在 runs/support-pressure-20261003。
资产/规划、训练拟合、独立验证、脚本demo、测量/估计压力及硬件结果分开。当前可部署控制不读当前接触/物体/滑块真值，不假设硬件力传感或电流接口。
