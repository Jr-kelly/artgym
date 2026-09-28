# 本轮五指侧夹复现

工作树 `/data/research/artgym-g2-finger-surface-20260928`，分支 `feat/g2-wuji-finger-surface-grasp-20260928`。本机使用 `/home/agiuser/miniconda3/envs/artgym/bin/python`、原 Isaac Gym、G2+Wuji 一代资产及冻结权重。不是新的训练环境，也不是已通过的完整任务。

运行器 `scripts/g2_local_launch.py` 为每次执行固定源码、记录全部参数和真实 PID；只允许新目录。本轮仍共享原 80 次控制额度，已用次数看 `runs/g2-finger-surface-20260928/state.json`。下面命令是复现入口，未自动重复执行。

## 连续物理诊断

F1-03（均衡布局，不加停稳或反馈）的完整命令；`--pickup-only` 明确不执行翻掌或策略：

```bash
cd /data/research/artgym-g2-finger-surface-20260928
python3 -m scripts.g2_local_launch \
  --experiment-directory g2-finger-surface-20260928 \
  --name replay-F1-03 --module scripts.run_g2_tabletop -- \
  --group B --operation-yaw 90 --yaw 180 --dx=-.05 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan configs/g2_finger_surface/balanced-side-pinch-v1.json \
  --acquisition-arm-seed configs/g2_finger_surface/balanced-side-pinch-v1-arm-seed.json \
  --cartesian-acquisition --slider-face down --table-localization settled-truth \
  --lift-height .30 --pickup-retention-hold 1 --pickup-only --only-grasp \
  --video --closeup --contact-diagnostics \
  --output /data/research/artgym-g2-finger-surface-20260928/runs/g2-finger-surface-20260928/replay-F1-03
```

- F1-04：相对上述命令只增加 `--closed-settle-seconds 1`，更换 name/output。
- F1-05：相对 F1-03 只增加 `--pickup-finger-feedback`，更换 name/output。该控制器实时读取刀和腕的仿真真值，非部署输入；不使用力矩传感器、外力或物体状态写入。
- F1-01/02：分别使用 `side-pinch-v1.json` / `side-pinch-squeeze4.json`，机械臂初值使用 `side-pinch-v1-arm-seed.json`。删除 `--pickup-only`，增加 `--air-flip 180 --air-flip-only`。实际两次都在取刀保持门槛失败，未执行翻掌。

每次原始精确命令和源码 pin 在 `F1-0N-launch.json`；两个 Release 增量包保留相应历史源码文件和全部哈希。原始 F1-01/02 的 source pin 分别为 `057ec2264442966b` / `42671b08e3a5d7e4`；F1-03/04/05 为 `c90fea75d2be3eb2` / `675bb62de6a2dad8` / `3d4fbaa333006b68`。固定资产、物性及 DOF 次序在每次 `physics.json`，冻结配置在 `frozen-config.yaml`。

原 teacher/student 路径沿用运行器 `PUBLISHED` 常量，来源是之前发布的 core teacher/student Release；本轮上述试验没有进入策略，不将载入权重等同于执行策略。本轮未更改或重新训练任何权重。

## 原始证据与评分

```bash
bash scripts/g2_local_python.sh -m scripts.summarize_g2_finger_surface \
  --run runs/g2-finger-surface-20260928/F1-03-balanced-pickup-hold \
  --output runs/g2-finger-surface-20260928/my-new-audit.json
firefox http://127.0.0.1:8767/g2-finger-surface-20260928/
```

查看 `trace.npz` 或失败时的 `partial-trace.npz`、`knife-contact-pairs.jsonl`、`pickup-hold-check.json`、`failure.json`。原 `report.json` 中相对旧缓存功能抓姿的评分不能替代本轮独立取刀保持评分。两段视频 `continuous.mp4` 和 `hand-closeup.mp4` 是同次执行同步录制；WebM 仅编码转换，没有剪接、加字或变速。

保持标准：固定 1 秒，世界和手内刀身平移分别 <10mm、旋转分别 <0.25rad，刀心高度 >0.85m（桌高 0.75m），无刀桌接触，记录全部五指接触。不能从刀曾被抬高或接触次数推断稳定支撑。伸缩仍要求 20 秒、外部时钟每 5 秒换向；本轮尚无对应成功数据。

## 几何规划

`scripts/search_g2_palm_down_pinch.py` 是有限初值触达求解；`scripts/audit_g2_side_pickup_candidate.py` 进行完整凸包相交核查；`scripts/plan_g2_side_pinch_motion.py` 检查开合和 G2 路径。所有几何输出不是物理成功。输入落稳位姿仅用于离线规划，真实执行仍从桌面初态启动、自然落稳后一次真值定位，不载入获取末态。

闭合预压是目标关节对应的几何压入量，不是手指测得的位置或力。手内反馈的首帧电机参考、动作范围、避碰拒绝和实际物体运动都单独记录，评分参考不会跟随物体刷新。

原先成功版本、权重和视频仍保留于独立 `g2-wuji-local-policy-20260928-v1` Release；不能用它替代本轮新布局的成功证据。

## 实测尺寸新资产 F1-07 / F1-08

实测/假设及结果见 [新刀报告](g2-measured-knife-20260928.md)。两个试验都是获取诊断，未执行teacher/student。F1-07停在接近前净空检查；F1-08执行闭合与抬起但没有取离桌面。不是完整任务demo。预算80/80已用完，下列是完整复现命令，本轮未自动重复执行。

F1-08（固定运行器pin `0cc7584737f0d607`）的等价运行命令；必须使用新输出目录。`--table-localization settled-truth`是自然落稳后的一次仿真真值定位，不是可部署视觉输入：

```bash
cd /data/research/artgym-g2-finger-surface-20260928
bash scripts/g2_local_python.sh -m scripts.run_g2_tabletop \
  --group B --operation-yaw 90 --yaw 180 --dx=-.05 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan configs/g2_finger_surface/measured-recorded-rest-pickup-v2.json \
  --acquisition-arm-seed configs/g2_finger_surface/measured-recorded-rest-pickup-v2-arm-seed.json \
  --knife-spec assets/objects/knife_wuji_measured_envelope_20260928_v1/000/asset-spec.json \
  --cartesian-acquisition --slider-face down --table-localization settled-truth \
  --lift-height .30 --pickup-retention-hold 1 --only-grasp --pickup-only \
  --video --closeup --contact-diagnostics \
  --output /data/research/artgym-g2-finger-surface-20260928/runs/g2-finger-surface-20260928/replay-measured-F1-08
```

F1-07相同参数，将plan/arm-seed改为`measured-rest-balanced-pickup-v1.json` / `measured-rest-balanced-pickup-v1-arm-seed.json`，使用新output；其原pin为`9d2343a27f1c2fe4`。F1-06旧刀的精确命令仍在增量03的`runs/F1-06-launch.json`中，不能换成新资产却沿用旧结果。

离线重建几何规划，不新增物理试验：

```bash
bash scripts/g2_local_python.sh -m scripts.search_g2_palm_down_pinch \
  --localization runs/g2-finger-surface-20260928/measured-recorded-rest-planning-localization.json \
  --output runs/g2-finger-surface-20260928/my-recorded-rest-touch \
  --refine runs/g2-finger-surface-20260928/measured-rest-balanced-touch/side-face-refine-00.json \
  --avoid-thumb-palm --balance-long-axis --balanced-margin --use-recorded-table-pose \
  --self-collision-audit runs/g2-finger-surface-20260928/known-path-self-pairs-for-retarget.json \
  --knife-spec assets/objects/knife_wuji_measured_envelope_20260928_v1/000/asset-spec.json
bash scripts/g2_local_python.sh -m scripts.plan_g2_side_pinch_motion \
  --plan runs/g2-finger-surface-20260928/my-recorded-rest-touch/side-face-refine-00.json \
  --localization runs/g2-finger-surface-20260928/measured-recorded-rest-planning-localization.json \
  --output runs/g2-finger-surface-20260928/my-recorded-rest-motor \
  --opening .005 --squeeze .004 --open-pad-lift .002 --close-via-touch \
  --arm-wrist-posture -.8 --flip-axis knife-length \
  --extra-self-pairs configs/g2_finger_surface/measured-motion-extra-self-pairs.json \
  --knife-spec assets/objects/knife_wuji_measured_envelope_20260928_v1/000/asset-spec.json
```

上述记录只用作离线规划输入；运行器依旧创建正常平放、闭刀滑块朝下的初始场景，真实执行自然落稳和全段电机控制。不能用记录直接重设运行中的手、刀、滑块。

离线几何/动态图检查入口：`audit_g2_measured_thumb_sweep.py`、`predict_g2_measured_rest.py`、`plot_g2_measured_pickup.py`。两次新资产结果的全部原始文件在Release增量03；恢复目录映射以包内`manifest-03.json`为准。源文件相同部分复用Git基线commit或前两个证据增量，不重复历史备份；所有源码pin均有哈希索引。
