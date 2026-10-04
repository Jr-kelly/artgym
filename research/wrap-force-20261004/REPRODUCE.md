# 恢复与运行（当前候选，持续更新）

本轮实验副本：`/data/research/artgym-experiments-20260921/wrap-force-20261004`。代码分支 `feat/wuji-wrap-force-20261004`；最终归档和 Release 清单将在交付时补齐。不能仅凭下载代码宣称恢复了权重和资产。

## 已冻结的连续仿真候选

在仓库根目录、现有 Isaac Gym Preview 4 / Python 3.8 环境运行：

```bash
/home/agiuser/miniconda3/envs/artgym/bin/python -m scripts.run_wuji_wrap_selected --output runs/wrap-force-recovery/nominal
```

该入口执行真实桌缘取刀、固定支撑换握、两轮 40 mm 命令、定时位置保持、功能评估及物理接触分析。输出 `simulation/continuous.mp4`、`hand-closeup.mp4`、`trace.npz`、全物理步接触记录和评估。保持有限 PD、重力、被动导轨、原力矩/速度约束；没有真机连接。位置保持不等于恒力，功能端点通过不等于实际完整 40 mm 或完全收刀。

冻结配置见 `FROZEN-CONTINUOUS-CANDIDATE-V10.json`，选定 actor 为 `runs/wrap-force-20261004/train/continuous-source2-pressure-thumb25-v2-localr1/update_000050.pth`，SHA256 `2fa454dfeb7d40f22a5bdf33e740e7fd3c41a6cc906b233fabb06cd90c161948`。较晚的更新不自动取代它。

必要桥接依赖：

| 文件 | SHA256 | 作用 |
|---|---|---|
| `runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth` | `2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8` | 原 teacher / normalizer |
| `runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth` | `bbf61592721300b1cf053de8246898a69989ed102b7a034da6fb47cc9a541dcd` | 2076 维 R800 编码器 |
| `research/robust-knife-family-20261003/data/repaired-seeds.npy` | 随恢复清单给出 | 既有初始化依赖，实际取刀使用明确 motor plan |

必须恢复 G2/Wuji 原资产、Hydra 配置和上述路径；保留基线 [antirotation Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-antirotation-grasp-20261004-v1) 的依赖说明，不重新下载全仓历史。Isaac Gym 安装来自已授权环境，不能用 PyPI 的同名包替换。

## 一次初始估计的尺寸适配

```bash
/home/agiuser/miniconda3/envs/artgym/bin/python -m scripts.run_wuji_wrap_selected \
  --initial-estimate runs/wrap-force-20261004/validation/geometry-inputs-corrected-v3/015/once-estimate.json \
  --knife-asset runs/wrap-force-20261004/validation/geometry-assets-v3/015/mobility.urdf \
  --output runs/wrap-force-recovery/estimated-geometry
```

初始估计是带误差的尺寸/滑块观测，规划器不读取资产 ID、当前物体或接触真值。物理资产只交给模拟器。入口先重算接近、闭合、换握、全行程的原几何/关节检查，失败则不执行。015 已有完整连续通过记录；012–014 的其他准备与失败必须按各自证据阅读，不能从持刀 reset 通过推断连续泛化。000–011 训练、012–015 留出划分保留。

## 可校准的轴向测力诊断

直接完整接触力通道当前仍不可用。串联弹性 cap/carrier 是修改滑块动力学的独立诊断，不是原任务直接 B 通道，也不是真机测力。动基座校准见 `runs/wrap-force-20261004/measurement/serial-moving-base-v6/report.json`，最大残差 0.001575 N。

运行命令保存在各实验 `jobs/<name>/identity.json` 的 `command` 中。选择已完成、接触有效的诊断：`measurement/source2-pressure-series-v5` 和 `measurement/index-wrap-pressure080-series-v8`。它们使用不同明确的布局/压力档位，不能将二者合写成相同条件的重复。

```bash
/home/agiuser/miniconda3/envs/artgym/bin/python -m scripts.analyze_wuji_serial_axial_force \
  --trial runs/wrap-force-20261004/measurement/index-wrap-pressure080-series-v8 \
  --calibration runs/wrap-force-20261004/measurement/serial-moving-base-v6/report.json
/home/agiuser/miniconda3/envs/artgym/bin/python -m scripts.plot_wuji_serial_axial_measurement \
  --trial runs/wrap-force-20261004/measurement/index-wrap-pressure080-series-v8
```

B 读数按 cap 世界加速度、质量、重力与实际施加的串联弹簧力反算，并对非拇指接触、端挡、地面接触作有效性标记。每步 960 Hz 原始数据、起动/中段/端部窗口、速度/位置与压力对齐；缺项保留 null。容量不能填充为力值，单次瞬时峰值不能称为重复起动力或持续能力。

## 离线控制和真机接入点

`offline/frozen-v10-legal-export-v1` 仅有 `clock_s, hand_measured_q, arm_measured_q, issued_hand_target` 四个字段；`offline/frozen-v10-replay-holds-v1` 有 600 帧控制结果及预热/延迟记录。重放器支持同样的合法压力估计和定时位置保持，不连接 SDK。与已发目标的最大差异 0.000975 rad，不能声称位级一致。

本地低负载一次记录中计算中位 3.13 ms、p95 5.42 ms；同时训练时另一次记录超过 30 Hz 帧预算。两者都是离线计算，不能宣称真实硬件实时性能。

Wuji 原生关节块顺序为 index、middle、pinky、ring、thumb，每指四关节；G2 为 idx61–idx67。实际 SDK 必须按名称核实顺序、单位、符号、时间戳、位置接口和 effort 含义。实物双向起动/沿程阻力、有效行程、完全收刀位置仍未测得。复用基线 REAL-MEASUREMENT.md / HARDWARE-PREPARATION.md；本轮不发送机器人动作。
