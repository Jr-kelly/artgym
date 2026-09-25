# Wuji 美工刀持续实验

当前分支的活动任务为 G2 桌面取刀→冻结策略，先读 [G2_TABLETOP_HANDOFF.md](G2_TABLETOP_HANDOFF.md) 及 `research/g2-tabletop-baseline-20260925.md`。新实验写入 `runs/g2-tabletop-v1`；旧目标记录仅供溯源，不能用旧的预置持刀成功代替当前桌面全段成功。

先读本目录 [WUJI_GOAL_HANDOFF.md](WUJI_GOAL_HANDOFF.md)。这是用户要求的无上下文续接入口。
每项实验开始/结束、配置/机器变动、结果或失败后更新该文档与
`runs/wuji-goal/journal/events.jsonl`。同步入口副本 `/data/research/artgym/WUJI_GOAL_HANDOFF.md`
以及可连接远端，记录证据、配置、时间、权重 SHA256、运行进程和下一步。

远端进程 PID 只在对应主机有效，历史心跳不代表仍在运行。所有重启使用新的运行目录，保留失败。
在途实验使用固定源码 pin，不直接修改其源码。使用 IsaacGym 前先导入 isaacgym，再导入 torch。
不得创建子代理；保留原仓库和原4090训练。仅运行有用计算，整机GPU四小时门槛26%，目标40%以上。
冻结策略、旧开发集、新独立验证、脚本演示和真机验证须分开报告。未满足原目标，不标记完成。
