# 本轮连续仿真复现

当前可运行的完整桌面流程为 V17：实际桌缘取刀、持稳、两次带阻力伸出—保持—缩回—保持。冻结750未重新训练；新抓姿适配和完整拇指 motor 轨迹形成了有效接触。40mm指令对应实测32.21/26.44mm伸出、6.49/1.99mm回程。通过本轮预先声明的功能规则；旧0.25rad规则仍失败，不代表实物40mm行程/完全收起、必要泛化或真机完成。

在仓库根目录，解压本轮 runtime 依赖包，使用既有 Isaac Gym Python3.8 环境运行：

```bash
bash research/antirotation-grasp-20261004/RUN-V17.sh runs/antirotation-grasp-20261004/my-v17
```

入口只运行仿真。输出目录必须不存在，产生36秒全景和手部近景视频、每物理步接触记录、真实控制轨迹、旧评分及新功能评分。原始命令见 jobs/actual-table-projected-grasp-frozen750-load2-v17/identity.json。每次复现可能存在物理后端和硬件差异，应查看实际评分，不把归档结果当成本机重新验证。

代码从新GitHub分支/Release tag获取，机器人/刀资产保留原始网格。runtime 包含匹配teacher、2076维R800及154维冻结750；训练包另外包含本轮候选的模型、Adam、RNG和配置，候选训练权重不替换V17冻结750。Isaac Gym及CUDA运行环境需使用已有合法安装，不以权重压缩包代替SDK。

本地本轮解释器为 `/home/agiuser/miniconda3/envs/artgym/bin/python`；设 `WUJI_PYTHON` 可选解释器。科学进程需 `PYTHONPATH=.:rl_games`、对应runtime库及 `PYTHONNOUSERSITE=1`。SSH、GitHub等host工具清除 `LD_LIBRARY_PATH`。Host Python没有NumPy/SciPy/Torch。

参考 `SIMULATION-RESULTS.md` 查看高阻力、厚刀柄、回程预压及训练失败，`HARDWARE-PREPARATION.md` 和 `REAL-MEASUREMENT.md` 为离线接口/实物测量准备。本轮没有自动真机动作。源码/资产、训练拟合、冻结开发评估、独立验证与真机结果分别记录。

同一初始估计只能应用一次：传入 nominal-calibration.json 后由运行器处理计划中的 initial_geometry_estimate；不得先手工修正该 calibration 再让运行器重复修正。旧回程分支的关节线性混合因原始自碰撞已拒绝，当前控制器使用单条连续参考路径。

续接先读 WUJI_GOAL_HANDOFF.md 和本目录STATE/PROGRESS；PID和利用率都须重新核验。最终Release尚在整理，已推送代码快照不等同于整个研究目标完成。
