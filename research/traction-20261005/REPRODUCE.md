# 恢复与单入口运行

这是G2右臂＋Wuji v1原尺寸美工刀的仿真交付。默认完整36秒桌缘取刀与两轮40 mm指令，基础制动容量0.35，原验收阈值不变。需要兼容CUDA环境、Isaac Gym Preview 4许可安装和上一轮Python依赖；不包含机器人SDK。不要用系统Python代替现有artgym运行环境。

## 下载

从[上一Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-wrap-force-20261005-v1)取得两个依赖包，无需下载整个历史：

| 文件 | SHA256 |
| --- | --- |
| wrap-runtime.tar.gz | 3641e30850d88a41a5db4c385ff06d50ca321bc1f47e6527cd23fdcbd1a43fab |
| wrap-learning-state.tar.gz | 519d9dc52d7cb1091da79901268933e8ccabfa908425bd1b1ccdc98ec84039b4 |

从[本轮Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-traction-20261005-v1)取得`traction-overlay.tar.gz`、`restore_wuji_traction.py`和`SHA256SUMS`。所有输入包放在同一下载目录。恢复器验证两个依赖包及所有增量文件；新目录不得已存在。

```bash
python restore_wuji_traction.py --baseline-dir ./downloads --overlay ./downloads/traction-overlay.tar.gz --destination ./traction-restored
cd traction-restored
export PYTHONPATH="$PWD:$PWD/rl_games"
export PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
python -m scripts.run_wuji_traction_selected --output runs/my-traction-demo
```

如环境需要，将其`lib`加入`LD_LIBRARY_PATH`，保持Isaac Gym在torch之前导入。上述目录内的脚本已包含固定的S120权重哈希验证；单入口自动运行仿真、原functional-criterion-v1评估及接触分析。查看`simulation/functional-evaluation.json`，不要只看历史`report.json/full_success`。

恢复时增加`--run`可自动在新目录执行一次无视频连续验证并生成`RESTORE-RESULT.json`。本轮已经实际执行一次，证据为`RESTORE-RESULT-V17.json`：本地0.35端点26.97／3.49／27.97／5.39 mm，原验收全部通过。恢复验证使用制作时的增量包；最终包仅追加报告、诊断脚本、验证输入和发布元数据，选定控制器、入口及运行依赖的内容哈希须与该次验证一致，见`RESTORE-FINAL-EQUIVALENCE.json`。

## 条件与重新分析

```bash
python -m scripts.run_wuji_traction_selected --load .2 --detent .2 --output runs/nominal020
python -m scripts.run_wuji_traction_selected --load .5 --detent .5 --output runs/highload050
python -m scripts.run_wuji_traction_selected --initial-estimate runs/traction-20261005/validation/regression-inputs-v18/nominal-axial-plus5mm/once-estimate.json --knife-asset runs/traction-20261005/validation/regression-inputs-v18/nominal-axial-plus5mm/mobility.urdf --load .2 --detent .2 --output runs/axial-plus5
```

`--no-video`只省渲染；`--observation-noise`、`--observation-bias`为非负噪声／偏差幅值，`--actuation-delay-frames`为0或1；这些是显式仿真验证条件，不是策略输入。`--initial-estimate`统一适配初始规划、碰撞代理、承托和全40 mm拇指路径，先做几何证书，再执行真实连续接触；物理资产只交给仿真器。每次必须使用新的输出目录。

选定配置为`research/traction-20261005/FROZEN-CANDIDATE-V13.json`，控制参考为`runs/traction-20261005/configs/cartesian-recenter-v12.json`。未选V10仍保留，用`run_wuji_wrap_selected --selection <manifest>`显式复现历史，勿覆盖冻结证据。

另下载并解压`traction-evidence.tar.gz`可以分析已记录结果。`DELIVERY-RESULTS.json`列出准确路径、原判据、实际分段位移、测量口径及null的B/C。远端绝对路径记录保留为来源信息；分析器仅将本轮远端证据根映射到恢复后的同一相对目录，不修改原轨迹。额外视频在Release单独下载，也嵌入HTML。

本轮没有新训练，因此没有新的训练恢复点；继续训练应使用原包的真实S120模型／优化器／RNG，并重新声明任务分布。空目录恢复是仿真验证，不等于新随机种子统计，更不是真机运行。
