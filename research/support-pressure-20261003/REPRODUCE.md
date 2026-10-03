# 恢复本轮 G2 + Wuji 承托实验

候选已冻结为750权重与staged承托，四个新独立条件完整结果0/4；具体失败见FINAL-REPORT.md。新Release发布与实际恢复启动见交付回执。先读 `STATE.json` 和 `HANDOFF.md`，不要按旧 PID 重启。所有入口仅运行仿真或离线推理，没有硬件运动调用。

## 环境与已有依赖

需要现有 ArtGym Python 环境、Isaac Gym Preview4、匹配的 PyTorch/CUDA，以及 GPU。已授权开发机当前有四张 H200；本地 RTX4090 用于实际连续视频。H200 当前无图形模式可运行，视频渲染会在进入物理前崩溃，不能把这个问题记成控制失败。

从仓库根目录运行，设置 `PYTHONPATH=.:rl_games`、`PYTHONNOUSERSITE=1`、`PYTHONUTF8=1`、`LD_LIBRARY_PATH=<Python环境>/lib`。仿真模块先导入 Isaac Gym 再导入 torch。SSH、gh、rsync 使用系统库环境；可复用 `scripts/host_tool_environment.py`。

大型旧资产和编码器引用[上一轮 Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-continuous-knife-robust-20261003-v1)，本轮不重复上传。需要的归档只有：

| 归档 | SHA256 | 用途 |
| --- | --- | --- |
| `wuji-g2-source-final.tar.gz` | `48ced1cd9718348822f0e4606afdbc754658335848d2f14b89951c77701449b3` | 既有源码、机器人资产和校准输入 |
| `models-and-recovery-final.tar.gz` | `d77aa5c8aef9acfdcf59afa543bc13a43d2e2f1daa82456ba63f9daf4a9062a2` | 从中按路径提取下列两份旧权重；历史模型无须全部复测 |

两份必要旧权重：

| 仓库相对路径 | SHA256 |
| --- | --- |
| `runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth` | `2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8` |
| `runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth` | `bbf61592721300b1cf053de8246898a69989ed102b7a034da6fb47cc9a541dcd` |

在新的恢复目录解压旧源码，再覆盖本轮源码与实验配置。原仓库中的用户修改不作为恢复目标。新 Release 的清单会列出本轮新增文件和权重，恢复只校验实际使用的包与候选，不开展全历史哈希审计。

## 连续仿真入口

冻结保留权重为 `runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth`，SHA256 `11f87269e7910380c6dab1fa8dcc26e53e40da0bd905a1ae40e7ffcf812b1a1d`。它含模型、Adam 和 RNG，恢复后开始新的物理 episode，不能声称续接了 PhysX 求解器内部状态。

入口依据带误差的公开初始估计进行同一 IK/承托适配；物理资产路径单独交给仿真。先创建下面命令所需的估计文件，或使用交付中的示例。输出目录必须不存在。

```bash
python -m scripts.run_wuji_support_demo \
  --estimate runs/support-pressure-20261003/offline-input-load163-v119-retry1/estimate.json \
  --checkpoint runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth \
  --knife-asset assets/objects/knife_wuji_support_train_20261003/s0002/mobility.urdf \
  --support-layout staged --takeover-seconds 16 \
  --load .5 --detent .5 --load-profile pulse --load-frequency 2.9 \
  --hand-friction .65 --knife-friction 1.8 \
  --noise .002 --bias .006 --delay-frames 0 --seed 2026100358 \
  --output runs/support-pressure-20261003/recovered-continuous
```

已记录的配对连续成功例是 `demo/raised1-staged-support-film-v97`；厚14 mm、原承托的成功例是 `demo/thick14-strong750-necessary-family-film-v80`。完整原始命令以相应 `jobs/*/identity.json` 为准；已从GitHub草稿下载核心包、复用两份旧归档，在一个新目录实际完成本命令的36秒连续流程并通过；回执actual-restored-startup-v145-results.json。这只是该开发条件的恢复验证。困难名义条件仍因刀身旋转失败，不能用凸起成功例宣称整个目标族完成。

本地渲染时增加 `--video`，生成未经阶段拼接的 `continuous.mp4` 和 `hand-closeup.mp4`；字幕用 `scripts/annotate_wuji_pressure_video.py`。仿真报告包含两轮端点、刀身漂移/旋转和每个实际240 Hz子步接触对法向贡献汇总。求解器阻力容量、模型估计力与实际接触法向力分别标注；尚未完整恢复切向摩擦合力。

## 训练续接与证据

每个 `jobs/*/identity.json` 保存完整命令、开始时间、源文件和父权重哈希；`result.json` 保存退出与耗时。`train/*/args.json`、`config.yaml`、`scene.json` 和 `learning.jsonl` 对应拟合设置，不作为冻结或独立验证。

新的操作前准备 pilot 为 `research/support-pressure-20261003/run_preparation_credit_learning_v116.py`：同一750模型/Adam/RNG、512环境、150更新，比较16秒接管、14.3秒接管和16秒后保持支撑残差。三组使用相同128帧rollout、GAEλ=.98和探索重置，保留原奖励/动作/力矩/物理判据。命令中的 `--updates 900` 是绝对更新数750→900。只有实际连续行为改善才追加资源。

## 离线推理与真机缺项

`python -m scripts.replay_wuji_support_commands --help` 接受且只接受 NPZ 的 `clock_s`、`hand_measured_q`、`arm_measured_q`、`issued_hand_target` 四个字段。包含至少50帧接管前的真实历史；提前准备候选显式使用 `--takeover-seconds 14.3`，推进仍从16秒开始。带九维合法模型特征的163维候选还需从14.1秒或更早提供校准历史，R800仍为2076维。

追踪文件的 `time` 是控制周期结束时间，发指令时钟为 `time-1/30`；`observed_q` 是周期开始的噪声测量。离线导出不要误减一个物理子步。离线入口只检查输入、推理和目标限位，不建立场景，不证明真实控制效果。

真机尚未运行。具体 SDK、G2 厂商接口、关节零位/符号、测量时间戳、有限位置目标/重力实现、初始刀位标定和实物阻力曲线仍待核实，见 `HARDWARE-PREPARATION.md`。没有默认触觉、实测指端力或真实电流输入。


## 新 Release 恢复

新交付使用 `release-manifest.json` 和每个归档的 `.manifest.json`。下载源码覆盖包与runtime包，以及上表两份旧依赖；训练状态和视频分别按需下载，避免恢复整套历史。

```bash
python scripts/restore_wuji_support_delivery.py \
  --artifacts /path/to/new-release-assets \
  --old-artifacts /path/to/old-two-assets \
  --destination /path/to/new-artgym
```

加 `--learning` 恢复本轮完整训练状态，加 `--media` 恢复视频/可浏览报告。它恢复文件，不安装Isaac Gym/Python；复用已匹配的运行环境。成功后切换到新根目录运行上面的36秒连续命令。公开下载地址和SHA256列于Release清单，恢复目录应为空。

训练续接使用保存的参数，避免重新执行freshAdam/探索重置：

```bash
python -m scripts.resume_wuji_support_training \
  --checkpoint runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth \
  --output runs/support-pressure-20261003/train/continued-new-run \
  --updates 800 --print-only
```

去掉 `--print-only` 才实际启动；更新数是绝对750→800，保存的模型、Adam、RNG和时钟/GAE恢复。新物理episode不是PhysX中途状态。该命令只是恢复入口，**本轮无证据支持按原机制继续长训**。最后四个坐标候选保留相同恢复方式及其checkpoint内固定先验，但不是最终采用策略。


新合法输入导出入口（仿真记录到离线重放）：

```bash
python -m scripts.export_wuji_support_replay \
  --episode runs/support-pressure-20261003/restored-continuous-startup-v145/continuous \
  --estimate runs/support-pressure-20261003/offline-input-load163-v119-retry1/estimate.json \
  --output runs/support-pressure-20261003/new-legal-replay-input
```

它根据physics.json中的真实关节名称核对20/7映射，只导出关节测量、已发目标和30 Hz指令时钟；没有运行中的刀体/接触/阻力输入。旧trace的臂关节是周期结束采样，不能在运动期间宣称逐位输入等价。162维估计器接口的零扩展克隆已重放600个实际恢复回合目标，最大差异约0.95微弧度；这个克隆未进行新的策略训练，不能当作162维行为成功。


观察器补充包是未采用路线，恢复时加 `--learning`。为了交付完整训练输入而不重复存储相邻50帧历史，两个数据文件按环境重排压缩，使用以下命令恢复原始样本/字段顺序：

```bash
python -m scripts.repack_wuji_observer_data --mode unpack \
  --input runs/support-pressure-20261003/observer-data-packed-v155/fit.npz \
  --output runs/support-pressure-20261003/observer-data-fit-v148/data.npz
python -m scripts.repack_wuji_observer_data --mode unpack \
  --input runs/support-pressure-20261003/observer-data-packed-v155/fresh.npz \
  --output runs/support-pressure-20261003/observer-data-fresh-v148/data.npz
```

一次fit数据往返已恢复相同原始NPZ SHA256；没有量化、删样本或改标签。辅助头 `observer-head-v149/best.pth` 是20 epoch开发选择，含模型/Adam/RNG，训练曾跑80 epoch；三份策略800权重均完整保存其恢复状态。拟合误差、开发配对和四个冻结独立结果分开解释，不能按真实资产ID在线挑权重。

## 最终交付分组与层次

新 Release 为 `wuji-g2-support-pressure-20261003-v1`。`release-manifest.json` 记录每个归档与旧依赖的字节数、SHA256和恢复分组；同名 `.manifest.json` 逐文件核验。默认依次恢复旧源码、两份指定旧权重、本轮 source/runtime，再覆盖 `support-final-records.tar.gz` 中最终源码增量与结果文档。后者必须最后应用，不能只使用较早打包的核心文档。`--learning` 再恢复完整训练状态，包括未采用观察器；`--media` 恢复视频。所有数据包角色明确，不把估计器拟合、恢复运行或开发展示称为独立验证。

`support-observer-recovery.tar.gz` 是本轮未采用候选：含三组750→800完整模型/Adam/RNG、冻结历史观察器及两份无损重排数据。原始812 MB数据重排后约147 MB，未量化或删样；先用上文命令还原行序再复训。默认恢复仍运行750/staged，不能因为新包存在就自动切换到162维候选。

HTML 直接内嵌七条完整视频，七条原始全景 MP4 为独立 Release 资产；近景和所有原始视频在 `support-movies.tar.gz`。失败和逐帧数据在 `support-evidence.tar.gz`。归档 STATE 是打包时的快照，公开发布与最终结束回执在分支最新 HANDOFF，不能把快照中的 PID 当成活跃事实。

新增162维观察器/冻结拇指完整800状态在同一恢复目录实际续到805；跨过16秒控制接管并执行有效残差优化，冻结拇指与观察器字节未改变，Adam/RNG保留。证据 `actual-observer-fullstate-resume-v158-results.json`。这仅验证恢复功能，重启物理训练样本存在大量失败，不采用805或将其称为新性能。
