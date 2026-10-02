# G2 + Wuji v1 连续取刀与带阻力适配（进行中）

本轮从 `1c45ef574d068d56e800cf22c51e1fc8f2c0fe2b` 接续，实验副本单独工作。
真实刀柄主体输入为135×16×12mm（不含滑块），无按下解锁。主体/滑块质量、摩擦、阻力和执行器模型仍是仿真工程假设。

当前证据：G2连续侧夹取刀和保持已完成一次（equilibrium-v7）；直接接R800后失稳，伸出未完成（continuous-v8）。不能把取刀视频或预置持刀子模块称作完整demo。

## 恢复运行

需要 Isaac Gym Preview4、ArtGym Python环境（本轮torch2.1/cu118），并恢复以下原始权重。

- `runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth` SHA256 `bbf61592721300b1cf053de8246898a69989ed102b7a034da6fb47cc9a541dcd`
- `runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth` SHA256 `2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8`

权重由本轮最终Release提供；目前也可按上一轮Release及其freeze.json按需恢复。设置 `PYTHONPATH=.:rl_games`、`LD_LIBRARY_PATH=<artgym-environment>/lib`、`PYTHONNOUSERSITE=1`。仿真模块必须先导入Isaac Gym再导入torch。

连续取刀—接管尝试，输出目录必须不存在：

```bash
python -m scripts.run_g2_robust_demo   --output runs/robust-knife-family-20261003/demo/recovered-continuous   --video --seconds 36 --dx=-.10 --dy=.05 --yaw=45 --slider-face down   --grasp-plan research/robust-knife-family-20261003/pinch-equilibrium-bounded-v2/motor-plan.json   --table-calibration research/robust-knife-family-20261003/g2-cartesian-calibration-v1.json   --cartesian-path research/robust-knife-family-20261003/g2-cartesian-path-v1.json
```

`--grasp-only --seconds 18`只验证拿取/保持。桌面位姿文件来自独立记录的仿真自然落稳状态，是一次性的理想离线校准；不是已接通相机，也不是运行时物体真值。过程中不重置物体，不固定刀体，不驱动滑块；动作和阶段切换只用预定时序、实际关节/FK、已发目标及真实50帧控制历史。

R800兼容性检查：

```bash
python -m scripts.audit_g2_r800_bridge --output runs/robust-knife-family-20261003/checks/recovered-parity
```

原始检查的2076维编码输入、合法actor观察和电机目标相符；证据 `runs/robust-knife-family-20261003/checks/g2-r800-bridge-v1/`。

联合尺寸/接触/阻力适配的正常基线训练：

```bash
python -m scripts.train_wuji_robust_residual   --output runs/robust-knife-family-20261003/train/recovered-A   --envs 1024 --updates 400 --randomization-scale .5   --load-max .10 --detent-max .10 --seed 2026100307
```

每50更新保存模型、Adam和RNG。`--resume <checkpoint>`恢复优化器，`--updates`是绝对更新数；物理回合重新开始，不是求解器逐位恢复。训练是预置功能抓姿的代理子模块；含四个来源，12个尺寸实例及连续随机接触、起动/变化阻力、观测/控制延迟扰动。`family-manifest.json`保存生成种子、来源及每个资产/抓姿哈希；独立4个尺寸实例目前尚未打开。

```bash
python -m scripts.evaluate_wuji_robust_residual   --output runs/robust-knife-family-20261003/dev/recovered-A   --checkpoint <checkpoint> --envs 96 --seed 2026100311   --randomization-scale .5 --load-max .10 --detent-max .10
```

不带checkpoint是冻结R800配对基线。开发评估不等于最终独立验证；`--heldout`用于新几何的独立检查，不能用于调参或挑选模型。所有初始尝试保留，先实际保持50帧，随后四段5秒命令；失败后不重置物理。最终报告和权重尚未冻结。

主要连续runner输出 `continuous.mp4`、`hand-closeup.mp4`、`trace.npz`、`plan.json`、`physics.json`、`report.json`。净接触力仅是诊断，不能冒充拇指与滑块接触对力。平衡计划中的牛顿数不是实测力或恒力闭环。0.10N是新增诊断负载上限的一种配置，不是实物阻力上界。

本轮接续状态以 `STATE.json`、`HANDOFF.md`、`DECISIONS.jsonl`为准；PID和利用率必须重新核实。本轮不向真机发动作，最低12小时工作尚未完成。
