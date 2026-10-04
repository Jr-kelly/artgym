# 恢复与运行

默认入口已切换到新包覆抓姿：真实桌角取刀、持稳、两轮 40 mm 伸缩命令；没有换握或定时位置锁存。冻结文件是 `FROZEN-WRAP-CONTINUOUS-CANDIDATE-V12.json`。当前选定 S120 权重 SHA256 为 `ad16a153c27eb01567c14422ca8ed23e5bebfc6e1c901683031f245631944d2a`，训练初始化来自 750；后续失败试训不能自动替代。

## 环境与恢复

Python 3.8、授权安装的 Isaac Gym Preview 4、PyTorch 2.1.0/cu118；依赖版本见 `runtime-pip-freeze.txt`。恢复包保留仓库相对路径。Isaac Gym SDK 本身不再分发，必须使用已有授权安装；不能用 PyPI 同名包替换。

解包代码/资产/配置和学习状态到同一空目录，校验恢复清单后，在该目录执行。将下面的 PYTHON 改为已有 Isaac Gym 环境的 Python：

```bash
export PYTHON=/home/agiuser/miniconda3/envs/artgym/bin/python
export LD_LIBRARY_PATH="$(dirname "$(dirname "$PYTHON")")/lib:${LD_LIBRARY_PATH:-}"
export PYTHONPATH="$PWD:$PWD/rl_games:${PYTHONPATH:-}"
"$PYTHON" -m scripts.run_wuji_wrap_selected --output runs/recovered-wrap/nominal
```

输出 `simulation/{continuous.mp4,hand-closeup.mp4,trace.npz,report.json,functional-evaluation.json}`，完整接触记录及选择/实际命令。此入口只有仿真，不连接机器人。

实际体根位置 x=.3035 m、y=−.6295 m、yaw45°，已知桌中心 y=−.23 m；没有刀身固定装置。29 g 主体与6 g滑块的组合重心位于桌内。位置偏置及 .8 N 压力代理属于有限 PD 电机目标/模型，不是恒力控制；实际法向压力由独立物理记录报告。旧冻结 localization 的文字不能替代上述实际数值。

## 恢复选定学习状态

```bash
"$PYTHON" -m scripts.resume_wuji_wrap_learning \
  --checkpoint runs/wrap-force-20261004/train/paired-held-single1-pilot-v1r1/update_000120.pth \
  --updates 121 --output runs/recovered-wrap/learning-resume121
```

实际空目录恢复已经完成一次更新、保存模型/Adam/RNG；该更新处于取刀前缀，尚无有效 actor 操作样本，不是能力提升。物理回合重新开始，不宣称逐位续接 PhysX 状态。失败候选的保存状态只用于复现分析，不默认继续训练。

## 带误差的一次尺寸估计

```bash
"$PYTHON" -m scripts.run_wuji_wrap_selected \
  --initial-estimate runs/wrap-force-20261004/validation/geometry-inputs-corrected-v3/015/once-estimate.json \
  --knife-asset runs/wrap-force-20261004/validation/geometry-assets-v3/015/mobility.urdf \
  --output runs/recovered-wrap/geometry015
```

统一规则：所有尺寸使用体根 x=.306 m；一次带误差的尺寸/滑块估计驱动接近、闭合、全40 mm参考的重新规划和原约束认证。物理资产只交给模拟器。缓存与 G2 映射、控制历史和手部重力均保持原实现。012–015 在该规则下均有实际连续通过记录，见 `DIRECT-CORNER-ONCE-ESTIMATE-CONTINUOUS-V14.json`。000–011 训练、012–015 留出及原抓姿划分不变。尺寸通过不等于阻力/观测噪声联合泛化已完成；.35/.5 N 与噪声挑战存在失败。

早期 source2 方案可显式执行 `--preset source2`；它有换握及已知时钟的位置保持，见 V10 冻结文件，不是默认包覆方案。

## 轴向测量

原刀完整接触切向力和导轨真实反力尚无通过校准的通道。串联弹性 cap/carrier 是修改动力学的独立诊断，不能当作原刀或真机测量。动基座校准最大残差 .001575 N，校准原始数据随证据包给出。用世界加速度、质量、重力及实际施加弹簧力反算轴向力，并筛除非拇指接触、地面和端挡；缺项为 null。

```bash
"$PYTHON" -m scripts.analyze_wuji_serial_axial_force \
  --trial runs/wrap-force-20261004/measurement/index-wrap-pressure080-series-v8 \
  --calibration runs/wrap-force-20261004/measurement/serial-moving-base-v6/report.json
"$PYTHON" -m scripts.plot_wuji_serial_axial_measurement \
  --trial runs/wrap-force-20261004/measurement/index-wrap-pressure080-series-v8
```

该样本是持刀诊断，不是取刀演示；配对 old/new 两种布局使用相同权重及压力档、各自匹配参考。实际 ±.20 N 中段推/拉读数属于修改装置 B 通道；法向压力 A、已知阻力容量、外加负载 D 都不能替代 B。起动窗口的瞬时峰值不能称为可重复起动力或持续能力。guide-reaction calibration 的失败记录必须保留，不对失败公式发布有效 C 反力值。

## 离线与真机准备

`offline/frozen-v12-legal-export-v1` 只含 clock_s、hand_measured_q、arm_measured_q、issued_hand_target。重放 r1 的600帧计算中位3.24 ms、p95 5.54 ms，但与记录目标最大差异 .01543 rad；这是离线计算，不是 SDK 实时/逐位一致证明。预热不发硬件命令。

Wuji 原生块顺序 index、middle、pinky、ring、thumb，各4关节；G2右臂 idx61–idx67。真实 SDK 尚需核实名称、顺序、单位、符号、时间戳、位置接口和 effort 含义。实物轴向双向起动/沿程阻力、完全收刀位置及有效行程仍需测量。`REAL-MEASUREMENT.md` 与 `HARDWARE-PREPARATION.md` 提供离线测量/接入准备。本轮没有自动真机动作。
