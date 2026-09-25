# G2＋Wuji 桌面取刀 → 冻结伸缩策略

2026-09-25：固定 A/B/C 均通过 20 秒两轮的 **10 mm 端点与全程稳定标准**。B/C 尚未全过 2 mm 严格诊断。20 次小变化验证已结束，B/C 各整段 0/10：9 次转腕掉刀、1 次端立倾斜超限，均未接管策略。详见 [最终报告](g2-tabletop-final-report.md)。这里的固定 1/1 均为选定的开发单案例，不是泛化成功率。

| 组别 | 案例 | 抓取 | 抓取后伸缩 | 整段 | 端点最大误差，mm | 行程，mm | 固定参考漂移，mm / rad | 2 mm |
|---|---|---|---|---|---|---|---|---|
| A 预置 → teacher | A-operation-up5-v63 | 不适用 | 不适用 | 1/1 | 0.612 / 0 / 0.379 / 0 | 40.417 | 7.113 / 0.156 | 通过 |
| B 实际取刀 → teacher | B-axis3-post-up5-teacher-v65 | 1/1 | 1/1 | 1/1 | 1.895 / 7.038 / 2.038 / 7.647 | 37.941 | 4.114 / 0.159 | 未全过 |
| C 实际取刀 → student | C-axis3-post-up5-student-ideal-v66 | 1/1 | 1/1 | 1/1 | 4.914 / 5.413 / 6.656 / 4.827 | 37.082 | 5.185 / 0.236 | 未通过 |

三个案例均无掉落。端点取每个 5 秒阶段最后 0.3 秒的最大误差；稳定要求操作全程相对接管时固定参考漂移 <10 mm、旋转 <0.25 rad。最后一帧达标不能代替窗口达标。

## 实际执行的路径与边界

B/C 从 75 cm 高的正常桌面、平放闭刀开始：侧夹抬起 → 在同一桌面端立 → 完全松手撤离 → 功能姿态重抓 → 再次抬起 → 承托倾斜并松拇指，让滑块被动回闭 → 恢复手指目标、返回并上倾腕部 5° → 停稳 → 冻结策略操作。获取 89 秒、操作 20 秒，共 109 秒，状态连续。

功能重抓相对原计划沿刀轴调整 3 mm，手指电机目标不变。原功能抓姿直接从平面取得会与桌面相交，因此增加了桌面支撑换握。此方案利用现有刀具模型的平端面；未使用桌边或夹具，真实刀具是否能如此稳定端立尚未验证。获取阶段的被动滑块移动不计作策略操作成功。

操作每 5 秒按仿真外部时钟换向，目标为原滑块下限及下限 +40 mm。操作动作全部来自冻结 teacher/student。没有操作阶段重置、吸附、刀具约束、隐藏外力或滑块位置驱动。仅在首次物理步前设置一次场景初始状态。

G2 采用目录内源资产的右臂、关节顺序和安装关系，非 Franka。手、刀物性和冻结权重未改；新增右臂伺服使用源增益的 10/20 倍及限幅关节积分，源力矩/速度上限保留，尚未硬件标定。原训练的手部无重力设置也保留。

接近/闭合时有 54 帧拇指或小指碰桌，网格最大穿入估计 0.211 mm；源 PhysX 接触偏移为 2 mm。臂/掌没有碰桌，操作时刀具没有桌面支撑。G2 源自碰撞关闭；非相邻臂/掌与机构凸包的采样检查没有检出重叠，仍不等于连续自碰撞认证。

## 接管与 student 输入

B/C 前 2670 帧获取轨迹逐项相同，有效物性文件也相同。初始电机参考使用真实最后命令，观测参考在接管时固定；RNN 只清零一次，50 帧历史来自实际停稳执行。冻结策略逐帧重放的观测、动作、手指目标误差为 0。

| Student 输入 | 当前来源 |
|---|---|
| 当前与初始关节角 | 仿真关节读数 |
| 指尖位置 | 读数 + 原 Wuji FK |
| 上一步动作与 50 帧历史 | 实际执行记录；接管前为停稳保持 |
| 开合目标 | 外部时钟命令 |
| 固定尺寸 | 原刀具资产 |
| 接管时刀身/滑块初始位姿 | 一次仿真真值 |
| 操作中的实时物体真值 | 不作为输入；扰动不变性审计误差为 0 |

**C 是理想初始化对照，不是可部署结果。** 获取规划还使用仿真定位做端立找正、测量释放、功能重接近及承托规划。视觉定位、实物端面与摩擦/驱动标定不在这次无真机基线中。

## 复现固定案例

在项目 README 对应的 Isaac Gym 环境与本独立分支运行。已有权重可直接复用；新环境只需下载这两个旧附件，无需整个历史备份：

```bash
mkdir -p weights/g2-frozen
gh release download wuji-experiments-20260923 --repo Jr-kelly/artgym \
  --pattern 'wuji-core-teacher-student-20260924-teacher.pth' \
  --pattern 'wuji-core-teacher-student-20260924-student.pth' --dir weights/g2-frozen
```

先运行 A；每次使用未用过的 `--name`，通过 `report.json` 检查结果：

```bash
python3 -m scripts.launch_g2_trial --name A-fixed-reproduce-001 -- \
  --group A --operation-yaw 90 \
  --operation-pose assets/robots/g2_wuji/plans/operation-knife-up5-v63.json \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --video --camera hand \
  --teacher weights/g2-frozen/wuji-core-teacher-student-20260924-teacher.pth
```

A 通过后运行 B。B 通过后将下列 `--group B` 改成 `--group C`、使用新名称，即为 student 理想初始化对照：

```bash
python3 -m scripts.launch_g2_trial --name B-fixed-reproduce-001 -- \
  --group B --operation-yaw 90 --yaw 180 --dx -.05 --wrist-posture -.7 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan assets/robots/g2_wuji/plans/edge-pinch8.json \
  --table-supported-seat --upright-yaw 250 \
  --table-regrasp-plan assets/robots/g2_wuji/plans/functional-body-face-axis3-v65.json \
  --level-standing-knife --standing-level-gate support-projection --measured-release \
  --gravity-close-before-takeover --gravity-close-support tray --gravity-close-yaw 30 \
  --post-acquisition-pose assets/robots/g2_wuji/plans/operation-knife-up5-v63.json \
  --video --camera hand \
  --teacher weights/g2-frozen/wuji-core-teacher-student-20260924-teacher.pth \
  --student weights/g2-frozen/wuji-core-teacher-student-20260924-student.pth
```

Launcher 默认 Python 为 `/home/agiuser/miniconda3/envs/artgym/bin/python`。其他安装路径在 `--name` 前用 `--python /实际环境/bin/python` 指定。输出位于 `runs/g2-tabletop-v1/<name>`，命令、源码哈希、日志与失败均保存；视频为 `continuous.mp4`，轨迹为 `trace.npz` 或 `partial-trace.npz`。

## 20 次预声明验证

[公开清单](g2-small-placement-validation-v1.json) 在第一项验证开始前已提交 `86b191b`；SHA256 为 `20f313a7f96681241a71a6d83b8f9a8db057947f888dbaa9caa7b718a8c5b7a1`。10 个共享位置，x/y±5 mm、yaw±2°，seed 2026092501，每个位置各跑 B/C。使用同一冻结源码与配置，不在该组上调参或更换失败样本。

本机清单已全部完成，driver 正常退出；以下命令读取已完成状态而不会重跑失败。其他中断副本续跑前须先核对 driver，不能同时启动两个：

```bash
python3 -m scripts.run_g2_small_variations run \
  --manifest runs/g2-tabletop-v1/g2-small-placement-v1.json --concurrency 2
```

在新工程复现完 A/B/C 后，可用对应试验名重新生成同 seed 的位置清单，再运行：

```bash
python3 -m scripts.run_g2_small_variations declare \
  --manifest runs/g2-tabletop-v1/reproduced-small-placement-v1.json \
  --a A-fixed-reproduce-001 --b B-fixed-reproduce-001 --c C-fixed-reproduce-001 \
  --seed 2026092501
python3 -m scripts.run_g2_small_variations run \
  --manifest runs/g2-tabletop-v1/reproduced-small-placement-v1.json --concurrency 2
```

结果写到清单同目录的 `*-results.json`。所有预声明位置都计入整段分母，包括规划失败；条件操作分母仅含成功获取。原始单案例及全部失败溯源见 [实验记录](g2-tabletop-baseline-20260925.md)，当前进程与下一步见 [续接入口](../G2_TABLETOP_HANDOFF.md)。
