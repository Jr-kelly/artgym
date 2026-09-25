# 在 Wuji 上复现 ArtManip

当前按论文推进的实现、验证结果与命令见 [paper_reproduction.md](paper_reproduction.md)。
下文的 `wuji_knife_demo` 是早期预求解轨迹演示，不能代表已训练成功或已完成真机部署。

可以沿用教师训练 → 学生蒸馏 → 仿真评估的流程，但需要为 Wuji 重新生成抓取并训练。
本次接入的是 ArtBot 的 **Wuji 右手**，固定手腕，未接入整机运动或真实硬件控制。

## 美工刀滑块 demo

默认视频已改为细身 NT A-300GR 尺寸参考：收刀外形 **147 × 19 × 11 mm**、
总质量 **35 g**。刀柄厚 8 mm，滑块凸起 3 mm；分件尺寸/质量仍有估计，来源见
[knife_reference.md](knife_reference.md)。刀片外观宽 9 mm，仅用于显示，无切割物理。

```bash
source /home/agiuser/miniconda3/etc/profile.d/conda.sh
conda activate artgym
cd /data/research/artgym
MAX_JOBS=2 python -m scripts.wuji_knife_demo
```

默认输出 `tmp/wuji-knife-demo/demo.mp4`，12 秒、一次伸出/回位，同时保存
`metrics.png`、`report.json` 和 `rollout.npz`。视频标有尺寸和脚本控制说明。
`--no-render` 只检查仿真；`--cycles` 可检查连续多次往返，检查不通过会报错。
新版按官方演示采用**指尖托持、拇指操作滑块**，刀头朝拇指/食指一侧。
本次单环境录制：滑块伸出 **35.68 mm** 后回到零，刀柄最大漂移 **1.54 mm**。
采样记录中掌部未接触刀柄；无名指指尖存在短暂失去接触，不宣称全程五指连续接触。

抓握和拇指轨迹针对新尺寸重新求解。仍为**脚本控制的接触仿真，不是强化学习策略或真机结果**。
刀柄可自由运动，滑块驱动刚度为零，只向手发送位置目标。启用跨手指和远端指节对掌部的
碰撞检查。演示摩擦系数为 3、滑动阻尼为 0.3；论文训练的阻尼为 1000，二者不可混同。
当前不含按压解锁机构。这套视频/轨迹不会进入论文训练的资产或抓取缓存。

可复现输入是 `assets/demo/wuji_knife/fingertip_preset.yaml` 和同目录 `slim/`；
脚本检查手和刀 URDF 哈希及关节顺序。真实部署还需要训练、动力学标定和硬件验证。
初态来自正式数据集 000 的第 52 号有效指尖抓取，预览轨迹在单独目录求解。
掌心包握不是论文复现的硬约束；后续实际使用中的受力与换握需要单独验证。

正式抓取库现增加同类姿势筛选：刀头朝拇指／食指、四指指尖托持、拇指能够在运动学上
覆盖 40 mm 滑块行程，并重新进行 2 秒物理稳定性检查。筛选前共有 35 个模型、
3,194 个有效抓取，筛选后 **35 个模型、1,187 个抓取**：811 个用于训练，
190 个用于同模型测试，186 个属于 5 个留出模型。独立筛选库为 `knife_wuji_fingertip`，保留原训练／测试归属；
完整阈值、最终统计位置和重跑命令见 [筛选流程](paper_reproduction.md#user-requested-fingertip-posture-filtering)。
原来的未筛选训练已停止并保留检查点，新实验使用 `runs/wuji_knife_fingertip_sapg`。
每个模型各取一个通过复验的姿势见 [35 模型总览](tmp/wuji-fingertip-filter/all-35-grasps.jpg)。

教师训练现支持同机四卡：给 `scripts.run_wuji_paper_pipeline` 增加 `--gpus 4`。
默认 4 × 2,560 个环境，共 10,240 个；总预算仍为 20.48 亿步，自动换算为 12,500 轮。
已在 `ssh -p 30296 wangjiarui@10.14.0.73` 的四张 H100 上跑通真实 PhysX 短训练、
四卡断点恢复和单卡权重迁移。在远端项目目录执行 `source scripts/activate_wuji_runtime.sh`
即可使用安装好的独立环境。四卡正式训练已于 2026-09-20 21:36 启动，目录为
`runs/wuji_knife_fingertip_4gpu`；本机 4090 实验继续运行。
四卡第 10 轮保存并评估，之后每 50 轮保存、每 100 轮后台评估；保留最近 6 个完整检查点
及每 500 轮快照。`evaluation/latest.json` 查看成功率，`checkpoints/latest.pth` 用于完整恢复。
训练运行中不表示滑块策略已经训练成功。
命令、恢复方式和测试范围见 [四卡训练](paper_reproduction.md#four-gpu-teacher-training)。

旧的 140 × 32 × 22 mm 厚刀柄示例及其种子保留作历史记录，可显式指定
`--preset assets/demo/wuji_knife/preset.yaml`。下节的早期抓取缓存和 bootstrap 检查
均针对这一旧模型，不是新版视频或正式论文数据集的结果。

## 本例的抓取缓存与训练

本例自行生成物体和候选抓取，因此无需等待未公开的物体/抓取生成子模块：

```bash
MAX_JOBS=2 python -m scripts.prepare_wuji_knife_training
```

此命令生成 192 个候选，调用原仓库 `ArtGrasp` 进行 4 秒重力保持验证，输出到
`caches/initial_grasp/wuji/knife_wuji_demo/000/`。当前得到 **33 条完整状态**（宽度 75），
其中训练集 26 条、测试集 7 条。它们来自同一把刀、少量种子的局部变化，并不代表跨物体
泛化能力。验证要求刀柄位移小于 10 mm、旋转小于 0.2 rad，拇指接触滑块且至少三个
其它指尖接触刀柄；没有跳过接触检查。

已用这些缓存跑通 **256 个并行环境、20 轮 PPO 教师训练**，检查点位于
`runs/wuji_knife_bootstrap/nn/last_wuji_knife_bootstrap_ep_20_rew__-41.1_.pth`，
日志为 `tmp/knife-demo/train-bootstrap.log`。这是训练链路验证，未达到操控策略验收标准；
上述视频使用参考脚本，不使用这个检查点。

继续训练可使用：

```bash
MAX_JOBS=2 OMP_NUM_THREADS=4 python -m isaacgymenvs.train \
  task=artmanip hand=wuji object=knife_wuji_demo \
  train=artmanipPrivLSTMPPO headless=True experiment=wuji_knife_ppo \
  task.env.numEnvs=1024 task.env.forceScale=0 task.env.jointNoise=0 \
  train.params.config.minibatch_size=16384 max_iterations=5000
```

`isaacgymenvs/cfg/object/knife_wuji_demo.yaml` 单独配置本例的质量、阻尼、摩擦和接触数，
保留原 `knife.yaml` 的设置。形成可用教师策略后，再按主 README 评估和蒸馏。

## 已接入的内容

- 从 `/data/research/ArtBot/G2_crsB_wuji/robot.usd` 提取 20 关节、26 刚体的右手和网格。
- `hand=wuji` 选择 `assets/hands/wuji_artbot/right.urdf`，配置位于 `isaacgymenvs/cfg/hand/wuji.yaml`。
- 添加掌部、指节、指尖碰撞几何，接触判定使用五个 pad link，按拇指到小指排列。
- 碰撞过滤按手部配置读取指尖名称，并保留源资产关闭自身碰撞的设置。
- 教师和学生观测维度按手配置，支持 PPO 和 SAPG；Sharpa 的原维度保持不变。

| 项目 | Sharpa | Wuji |
| --- | ---: | ---: |
| 动作维度 | 22 | 20 |
| 教师策略观测 | 117 | 111 |
| 特权观测 | 21 | 21 |
| critic 额外接触观测 | 5 | 5 |
| 学生每步本体观测 | 44 | 40 |
| 学生初始观测 | 57 | 55 |
| 学生总输入（50 步历史） | 2257 | 2055 |
| 完整抓取缓存单行宽度 | 79 | 75 |

资产、动力学和碰撞近似的来源见 [资产说明](assets/hands/wuji_artbot/README.md)。

## 运行检查

```bash
conda activate artgym
cd /data/research/artgym
python -m scripts.check_hand --hand wuji
```

默认进行 360 步开合运动并检查关节限位及有限值，视频保存在 `tmp/wuji-check/hand.mp4`。
加 `--cpu-pipeline --output tmp/wuji-check-cpu` 可检查 README 抓取验证所用的 CPU pipeline。

```bash
ARTGYM_SIM_HAND=wuji python -m unittest discover -s tests -p test_hand_adaptation.py -v
ARTGYM_SIM_HAND=sharpa python -m unittest discover -s tests -p test_hand_adaptation.py -v
```

集成测试使用临时生成的两连杆物体和合成状态，验证任务观测、20 维动作、教师网络和
学生编码器的前向/反向传播；这些状态不是合格抓取，也不会留在正式抓取缓存中。

2026-09-20 本机验证通过：GPU/CPU pipeline 各 360 步开合；Wuji 完整任务 4 个环境运行
16 步，教师和学生网络反向传播均为有限值；五个指尖均测得物体碰撞产生的非零接触力；
Sharpa 的任务与网络回归测试也通过。日志分别位于 `tmp/wuji-hand-gpu.log`、
`tmp/wuji-hand-cpu.log`、`tmp/wuji-task-test.log` 和 `tmp/sharpa-regression-test.log`。

## 扩展到论文中的多物体任务

主项目的 `make_data`、`func_lygra` 子模块仍不可访问，仍缺少论文中的多物体资产、
生成的抓取及预训练权重。本例只补齐了单把参数化美工刀。扩展到其它实例时，需要
物体资产及其 `lbx.json`，并基于本次导出的 Wuji 运动学生成初始抓取：

```text
assets/objects/knife_30/lbx.json
assets/objects/knife_30/000/mobility.urdf
caches/initial_grasp/wuji/knife_30/000/qpos.npy
caches/initial_grasp/wuji/knife_30/000/opos.npy
```

`qpos.npy` 是 `(N, 20)`，关节顺序必须与 `wuji.yaml` 的 `dof_names` 一致。
`opos.npy` 是 `(N, 4, 4)`，表示物体相对于手根坐标系的变换。`N` 必须能被验证时的
`--num-envs` 整除。不能直接使用 Sharpa 或仓库原版 Wuji URDF 生成的抓取缓存。

数据就绪后可运行：

```bash
python -m isaacgymenvs.valid_grasp \
  --hand wuji --object knife --asset-dir knife_30 --instance-id 000 \
  --pipeline cpu --num-envs 500 --episode-length 30 \
  --rot-threshold 0.1 --pos-threshold 0.01 --no-split --headless --camera

python -m isaacgymenvs.train \
  task=artmanip hand=wuji object=knife asset_dir=knife_30 \
  train=artmanipSAPGPrivLSTMPPO headless=True experiment=wuji_knife_sapg \
  task.env.numEnvs=1024 task.env.graspSplit=valid \
  train.params.config.expl_coef_block_size=256 \
  train.params.config.minibatch_size=16384
```

这里给出的多物体训练规模是起步配置，尚未进行论文物体的训练或成功率评估。之后按主 README
运行评估、蒸馏、推理，将 `--hand` 改为 `wuji` 并使用新训练的 checkpoint。

真实 Wuji 部署还需要 Wuji SDK 驱动、动作与反馈顺序映射、初始状态提供器，以及关节和
接触参数标定；当前 `deploy/sharpa` 的驱动不能直接控制 Wuji。
