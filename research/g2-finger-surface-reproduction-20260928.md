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
