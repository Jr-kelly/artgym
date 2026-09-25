# G2＋Wuji 桌面取刀基线（持续更新）

续接入口：[G2_TABLETOP_HANDOFF.md](../G2_TABLETOP_HANDOFF.md)。独立分支 `feat/g2-wuji-tabletop-20260925`，本机工程 `/data/research/artgym-g2-tabletop-20260925`，实验目录 `runs/g2-tabletop-v1`。旧成功版本及训练 PID 88339 保留；本阶段没有训练新策略。

截至 2026-09-25 18:00 CST：A 已通过；真实桌面侧夹、抬升、搬运、停稳已通过一个固定案例。该侧夹直接接 teacher 会掉刀，B 全段尚未成功；C 尚未运行。不能把抓取子阶段成功写成 teacher＋student 全流程成功。当前重点是从侧夹连续就位到原功能抓姿。20 次扰动验收尚未开始。

## 模型、控制及约束

- 源资产为用户目录 `/data/research/ArtBot/G2_crsB_wuji/robot.usd`，附属 USD 层与 config 同目录。导出 88 链接、87 关节；右臂 `idx61_arm_r_joint1` 至 `idx67_arm_r_joint7` 七自由度，加原 Wuji 右手 20 自由度。其余关节固定零位。没有沿用 Franka 参数。
- 末端父坐标 `arm_r_end_link`，Wuji 子坐标 `hand_r_base_link`，安装平移 `[0,0,0.0341]` m、旋转 `Rz(-90°)`。USD 的非平凡 child joint frame 按完整变换导出。逐项质量、惯量、限位、驱动、来源哈希见 [audit.json](../assets/robots/g2_wuji/audit.json)。腕部 FK 与实际仿真轨迹差约 1 μm / 2.4e-6 rad。
- G2 源驱动 100 Nm/rad、1 Nm·s/rad。有效 A 对照在此驱动下完成开合，但世界漂移 79.7 mm；当前右臂驱动改为 1000/20，保留源力矩及速度上限。后续增加关节误差积分 1/s，积分限幅 0.08 rad，只经有限力矩驱动写关节目标。此为仿真控制调试，未经真机标定。
- G2 缺失的碰撞体以逐链接视觉凸包补齐；按源配置禁用 G2 内部自碰撞，并排除臂手接缝；保留原 Wuji 手指碰撞过滤。机器人与刀、桌面碰撞开启。此模型不构成完整自碰撞规划验证。
- 原手/刀质量、摩擦、驱动与冻结模型保留。刀具 147×19×11 mm、35 g；刀身厚 8 mm、上方滑块厚 3 mm。滑块刚度为 0，无动作直接驱动滑块。原训练手部禁用重力的设置保留；G2 臂和刀具启用重力。
- 仿真为 Isaac Gym / PhysX，物理 120 Hz、控制 30 Hz。该运行库对 G2 actor 的 DOF 力传感器返回不支持；v12 起力矩数组为 NaN，不宣称实测扭矩。保留关节速度、实际角度、目标、物体位姿及逐手指接触配对。
- 桌面高 0.75 m，刀具正常平放。全部状态写入限于第一帧物理执行之前；抓取开始后只写电机目标。无刀具焊接、吸附、外力保持或缓存抓姿重置。

## 已完成对照及失败

以下均为开发案例，修改了抓法或控制参数，不能混合成冻结方案的泛化成功率。

| 实验 | 抓取/接管 | 伸缩结果 | 稳定性或失败 |
|---|---|---|---|
| A-g2-initialized-v4 | 预置 | 20 s 四端点均 <2 mm，行程 40.019 mm | 世界漂移 8.450 mm，通过 |
| A-g2-source-gains-v4 | 预置，源臂驱动 | 四端点均 <2 mm | 世界漂移 79.714 mm，不稳定 |
| A-g2-integral-v12 | 预置，新臂控制 | 四端点均 <2 mm，行程 40.090 mm | 世界漂移 7.744 mm / 0.150 rad，通过 |
| B-direct-grasp0-v5 | 未抬起 | 未操作 | 原功能抓姿手指穿桌约 40–44 mm |
| B-rolled-…-v7/v8 | 未抬起 | 未操作 | 抬高避桌则错过刀；下探仍未形成夹持 |
| B-edge-…-v9/v10 | 未抬起 | 未操作 | 接触主要在上表面，未形成有效侧夹 |
| B-normal-squeeze-grasp0-v12 | 抬升 20 cm，搬运掉落 | 未操作 | 4 mm 电机目标预压不足以保持搬运 |
| B-pinch8-transport-grasp0-v14 | 抬升、搬运、停稳成功 1/1 | 该诊断未请求操作 | 8 mm 电机目标预压，实际关节被接触阻挡 |
| B-pinch8-teacher-grasp0-v15 | 接管前抓取成功 1/1 | 条件开合 0/1，全段 0/1 | 相对原操作抓姿约 92° 差，接管后掉刀，0 完整循环 |
| B-normal-seat-grasp0-v13 | 抬升后直接插值就位 | 未操作 | 就位掉落 |
| B-contact-seat-grasp0-v16 | 抬升后 | 未操作 | 中途 IK 解分支跳跃，门禁中止，保存部分轨迹 |
| B-yaw90-contact-seat-grasp0-v17 | 抬升成功，就位掉落 | 未操作 | 连续 IK 可达，但自由刀身偏离预规划接触 |
| C | 尚未执行 | N/A | 先解决 B 的末态与接管 |

v1–v3 的早期 A 失败来自在 `prepare_sim` 前初始化的接口错误，均保留；不能以这些失败证明改物性的必要性。v4 将唯一 episode 初始化移至 prepare 后、首次 simulate 前，并恢复原环境首帧观测语义，A 恢复成功。

`plan_g2_edge_grasp.py` 的几何侧夹约束已从最近顶点改为相对侧面支持点。`plan_g2_seating.py` 求解保持接触的腕部＋手指目标；有界腕部平移调整使中间接触几何残差 <0.1 mm，但物理验证仍失败。v18 仅在就位阶段增加实时仿真物体位姿反馈，明确为 oracle 定位对照，结果待收集。

## 策略接管与数据来源

冻结 teacher SHA256：`4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac`。冻结 student 为既有 latent MSE final1000。使用先前公开权重，不重新训练。

所有位置/姿态按**实际测量腕部坐标**变换。初始参考在接管时固定；支持指动作围绕实际最后电机目标，拇指为逐步增量；RNN 仅在接管时清零。默认停稳 2 s，student 使用最后 50 帧实际关节角与零保持动作历史。操作阶段为外部时钟 20 s，每 5 s 换向，目标是原下限与下限＋40 mm，与仿真到位信号无关。

| Student 输入 | 本阶段来源 | 部署所需来源 |
|---|---|---|
| 当前/初始关节角 | 仿真关节读数 | 编码器 |
| 指尖位置 | 关节角＋相同 Wuji FK | 标定 FK |
| 上一步动作、50 帧历史 | 实际执行/停稳记录 | 实际执行记录 |
| 开/关目标 | 外部时钟 | 外部任务命令 |
| 固定几何尺寸 | 资产尺寸 | 实物尺寸 |
| 接管时刀身及滑块初始位姿 | 一次仿真真值 | 视觉/标记/其他独立估计，尚未实现 |
| 实时物体特权量 | 操作时不读取 | 不需要 |

因此 C 的初始化只能称“理想初始化对照”。如采用 v18 的就位控制，抓取阶段另含实时真值定位，也要单列；不能宣称可部署。接口审计 teacher 观测/动作误差约 1e-7；student 输入误差 1.19e-7、动作 2.32e-6；更改实时物体真值不改变 student 操作输入。

## 复现

在按本项目 README 安装的 Isaac Gym Python 3.8 环境运行。资产、功能抓姿已在此分支，G2 无需再次导出。若需重导出，执行 `python -m scripts.export_g2_tabletop --help`；读取 USD 的 Python 必须安装 usd-core。

先下载原权重（复用旧 Release，不重复上传）：

```bash
cd /data/research/artgym-g2-tabletop-20260925
mkdir -p weights/g2-frozen
gh release download wuji-experiments-20260923 --repo Jr-kelly/artgym \
  --pattern 'wuji-core-teacher-student-20260924-teacher.pth' \
  --pattern 'wuji-core-teacher-student-20260924-student.pth' --dir weights/g2-frozen
```

A，预置→teacher（每次使用新的 `--name`）：

```bash
python3 -m scripts.launch_g2_trial --name A-reproduce-001 -- \
  --group A --operation-yaw 90 --arm-gain-scale 10 --arm-damping-scale 20 \
  --arm-integral-gain 1 --video --camera hand \
  --teacher weights/g2-frozen/wuji-core-teacher-student-20260924-teacher.pth
```

B，已经完成的侧夹→teacher 失败基线，保留完整状态与视频：

```bash
python3 -m scripts.launch_g2_trial --name B-direct-takeover-001 -- \
  --group B --operation-yaw 90 --yaw 180 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan assets/robots/g2_wuji/plans/edge-pinch8.json --video --camera hand \
  --teacher weights/g2-frozen/wuji-core-teacher-student-20260924-teacher.pth
```

当前就位反馈对照（仍是实验，不能预告成功）：

```bash
python3 -m scripts.launch_g2_trial --name B-oracle-seating-001 -- \
  --group B --operation-yaw 90 --yaw 90 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan assets/robots/g2_wuji/plans/edge-pinch8.json \
  --seating-plan assets/robots/g2_wuji/plans/contact-seating.json \
  --seat-seconds 8 --seat-feedback object-truth --video --camera hand \
  --teacher weights/g2-frozen/wuji-core-teacher-student-20260924-teacher.pth
```

C 的命令是在冻结的 B 命令上改为 `--group C` 并增加 `--student weights/g2-frozen/wuji-core-teacher-student-20260924-student.pth`。当前不把这条可运行接口命令当作已验证的 C 结果。其他 Python 环境通过 launcher 的 `--python /path/to/python` 指定。

每次试验自动复制独立源码 pin、保存 SHA256、完整命令及日志。结果包括 `report.json`、`trace.npz`、`takeover.json`、`physics.json`、规划数据和无文字 `continuous.mp4`；中止试验保存 `failure.json` / `partial-trace.npz`。用 Isaac Gym 环境的 Python 执行 `-m scripts.audit_g2_trajectories` 汇总轨迹审计。

指标分开记录：抬升、抓取到接管、抓取后的条件开合、全段；每个 5 s 端点末 0.3 s 的 10 mm 基本标准与 2 mm 诊断；刀身世界漂移 10 mm / 0.25 rad 稳定、手内相对漂移及掉落。漂移参考仅在接管时固定。没有抓取成功时，条件伸缩为 N/A。首次固定方案真正接通后再冻结、预注册约 20 个位置/朝向变化，保留全部失败。
