# 本轮连续仿真复现

当前可运行的完整桌面流程为 V17：实际桌缘取刀、持稳、两次带阻力伸出—保持—缩回—保持。冻结750未重新训练；新抓姿适配和完整拇指 motor 轨迹形成了有效接触。40mm指令对应实测32.21/26.44mm伸出、回缩末端位置距仿真导轨下限6.49/1.99mm。通过本轮预先声明的功能规则；旧0.25rad规则仍失败，不代表实物40mm行程/完全收起、必要泛化或真机完成。

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


新增统一入口（从本轮Release源码启动，先在仓库根解压 runtime-v2 与 evidence 配置包，激活已有合法Isaac Gym环境）：

```bash
python -m scripts.run_wuji_antirotation_delivery_demo --case nominal --output runs/antirotation-grasp-20261004/my-nominal
python -m scripts.run_wuji_antirotation_delivery_demo --case height4 --output runs/antirotation-grasp-20261004/my-height4
python -m scripts.run_wuji_antirotation_delivery_demo --case higher-load-failure --output runs/antirotation-grasp-20261004/my-high-load
python -m scripts.run_wuji_antirotation_delivery_demo --case thin-failure --output runs/antirotation-grasp-20261004/my-thin
```

入口清楚标注原结果的开发/失败角色，保持原指令，自动运行新旧评分。`--show-command`只打印参数，不运行物理。原始权重/轨迹哈希见本目录`DEMO-COMMANDS.json`；新机器结果必须以新输出实际视频/评分为准。高度成功例实测36.16/31.54mm伸出、回缩末端位置距仿真导轨下限6.79/3.87mm，属于同一750加初始估计统一适配的已知高度开发例，不能推广为全尺寸泛化。

本轮冻结新5秒接管训练权重与模型/Adam/RNG另外放在learning包；750最强开发例仍使用runtime的原权重。若恢复本轮早期负训练且配置引用旧dense软链接资产，使用`--training-asset-registry research/antirotation-grasp-20261004/PHYSICAL-TRAIN-GEOMETRY.json`替代八个实际使用训练资产，字节相同的可移植副本已随源码保留。对于新的严格16场景与24必要形态配置，使用其自身registry，保持帧/场景/采样配对一致，不用替代registry改变原形态。

完整24初始估计/12物理形态配置：`runs/antirotation-grasp-20261004/complete-necessary-geometry24-v1/{scene24.json,registry.json,schedule1536.json}`；每个形态两次独立带噪声初始估计，重采样只在新回合。该配置本轮尚未训练，不包含能通过高度全范围的权重。它是继续有意义几何训练的准备，不是泛化成果。

可浏览报告及四个带力字幕双视角MP4单独公开；movies包同时保留原全景/手部近景，未剪切、不拼阶段。字幕使用评估真值，并明确法向贡献不含摩擦牵引力、容量不等于实物阻力。旧轮V138参数与本轮不匹配，仅作接触形态对照。


新5秒接管和有限无名指关节滞后搜索的代表性失败也使用统一入口，不改变原判据：

```bash
python -m scripts.run_wuji_antirotation_delivery_demo --case newprefix-thin-failure --output runs/antirotation-grasp-20261004/my-newprefix-thin-failure
python -m scripts.run_wuji_antirotation_delivery_demo --case ring-tracking-failure --output runs/antirotation-grasp-20261004/my-ring-failure
```

第一条额外解压learning包中的冻结50；第二条仍为runtime原750。滞后搜索是有限位置目标调整，不是测得接触力或恒力。

新5秒接管实验权重的模型/Adam/RNG恢复入口（已实际执行range04的50→51一次更新，51不用于晋升）：

```bash
python -m scripts.resume_wuji_antirotation_training --range 04 --updates 51 --output runs/antirotation-grasp-20261004/my-resume04
```

同样可用`--range 12`查看对应命令，只有range04本轮作过实际恢复检查。入口默认只再执行一个真实训练更新，开始新物理回合；不是建议延长已失败的训练路线。没有默认无限续训、SDK或机器人动作。
