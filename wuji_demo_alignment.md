# Wuji 美工刀：对齐成功 demo 的 RL 对照

本实验用成功视频的同一把刀、同一个初始抓姿和同一套接触物理，检查 SAPG 是否能够学会伸出/收回滑块。它是单任务学习验证，不能作为未见物体泛化或真机标定的结果。

原有 `wuji_knife_fingertip_sapg` 和 `wuji_knife_fingertip_4gpu` 保持运行。本实验使用独立配置、数据目录和 checkpoint。

## 已对齐的条件

| 项目 | 新实验 |
| --- | --- |
| 刀具 | 成功 demo 原始 URDF，147 × 19 × 11 mm |
| 刀柄/滑块质量 | 29 g / 6 g |
| 物体表面摩擦 | 3.0 |
| 滑块阻尼/刚度 | 0.3 / 0 |
| 滑块关节摩擦/armature | 0.001 / 0.001 |
| 手关节 PD | 与 demo 相同，刚度约 100、阻尼约 1 |
| 手表面摩擦 | 1.0 |
| 重力 | 刀具自由、重力开启；手基座固定、手重力关闭 |
| 手自碰撞 | 相同的 digit_filtered 规则 |
| 时间步 | 1/120 s，4 个物理子步，120 Hz 更新关节目标 |
| 控制 | 全部 20 个关节的绝对位置目标，无动作平滑 |
| 初始状态 | 同一个抓姿，包括实际关节位置和抓握目标的区别 |
| 随机化 | 关闭物性随机化、外力和关节观测噪声 |

策略动作通过初始抓握位置归一化：动作 0 表示保持初始目标，动作 ±1 对应关节上下限。所有关节仍由策略控制，能覆盖完整关节范围。输出层均值初始化为零，初始动作标准差为 `exp(-4)`。这是初始抓握先验，没有冻结支撑手指，也没有向 RL 输入演示轨迹、演示动作或轨迹相位。

滑块目标仍为 40 mm 和 0，容差 5 mm。与视频验收一样取消随机停留要求；一个训练回合完成伸出/收回后结束，最长 12 秒。奖励各项权重、方程和课程沿用当前 ArtManip，不把动作重放的成功算作策略学习成功。120 Hz 下每秒奖励采样次数与原 30 Hz 实验不同，需要用固定评估成功率比较。

## 重放与启动

在 artgym Python 环境中，从仓库根目录执行：

```bash
python -m scripts.prepare_wuji_demo_aligned
python -m scripts.check_wuji_demo_alignment \
  --num-envs 32 --pipeline gpu \
  --output tmp/wuji-demo-aligned-check/gpu-replay
python -m scripts.run_wuji_demo_aligned_training \
  --run-dir runs/wuji_demo_aligned_sapg \
  --gpu 2 --envs 640 --epochs 1000 \
  --preflight-report tmp/wuji-demo-aligned-check/gpu-replay/report.json
```

只有重放诊断脚本读取参考轨迹。它把绝对关节目标转换为 RL 动作，并通过真实 `env.step` 接口执行；训练 task 不读取参考轨迹。重放诊断延长终止预算，以便记录完整 12 秒，不改变接触物理。

对照训练预算为 640 并行环境 × 16 步 × 1000 轮，即 10,240,000 transitions。每 25 轮保存恢复 checkpoint，每 50 轮评估，第 10 轮提前保存并评估；保留最近 6 份恢复 checkpoint 和每 250 轮的里程碑。评估读取独立、不可变的权重文件，结果位于 `evaluation/latest.json`。

评估重复同一个训练抓姿 5 次、无随机化，检查确定性策略能否完成完整循环。它不代表 5 个不同抓姿，也不代表泛化成功率。是否学会必须看策略评估，不能从参考重放通过推断。
