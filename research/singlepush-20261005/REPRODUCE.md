# 单次推动和保持复现

使用兼容Python3.8/Torch1.13/Isaac Gym Preview4环境，在恢复根目录运行（先导入Isaac Gym，避免torch动态库冲突）：

```bash
python -m scripts.run_wuji_singlepush_selected --output runs/my-singlepush
python -m scripts.run_wuji_singlepush_selected --load 1.25 --output runs/my-load125
python -m scripts.run_wuji_singlepush_selected --load 1.5 --no-video --output runs/my-load150
python -m scripts.run_wuji_singlepush_frozen_case --case near-large --output runs/my-near-large
python -m scripts.run_wuji_singlepush_frozen_case --case shift-delay --output runs/my-shift-delay
python -m scripts.run_wuji_singlepush_frozen_case --case near-small --output runs/my-near-small
```

每个输出是新目录。入口校验冻结源码/配置/权重；完整22秒真实重力/接触仿真，从桌缘取刀连续换握，16秒开始35mm已知时钟命令，20.033秒后位置保持，不回收。正式判据为`extension-evaluation.json`：从15.7–16秒主动推进前滑块位置计算，末态严格>20mm、保持约1秒、承托/接触/机械端挡检查全部通过。原始native report仍保留共用运行器的历史双循环字段，**不能作为本轮评分**。

反馈只有测量关节、实际G2 FK、命令/历史/时钟、一次初始几何估计。没有滑块位移、真实刀姿态、接触力或阻力ID输入。阻力和资产只提供给仿真/离线评价。统一几何recipe生成换握和运动轨迹；失败规划保留，不切换手选权重。新冻结near-small在35mm末端自碰撞证书失败，预期返回未执行结果；其余两项当前完整通过。

## 空目录恢复

不重新打包既有大型依赖。使用[既有wrap Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-wrap-force-20261005-v1)的两个归档：

- `wrap-runtime.tar.gz` SHA256 `3641e30850d88a41a5db4c385ff06d50ca321bc1f47e6527cd23fdcbd1a43fab`
- `wrap-learning-state.tar.gz` SHA256 `519d9dc52d7cb1091da79901268933e8ccabfa908425bd1b1ccdc98ec84039b4`

新增小型`singlepush-overlay.tar.gz`已经包含新刀资产、选定actor、所有新增代码、共同recipe输入和冻结配置，不需要另下旧newknife/highload覆盖包。带授权的Isaac Gym运行时须已安装。恢复器校验依赖SHA256及覆盖包逐文件哈希：

```bash
python -m scripts.restore_wuji_singlepush --baseline-dir /path/to/wrap-archives --overlay /path/to/singlepush-overlay.tar.gz --destination /path/to/new-empty-directory --run
```

运行时设置`PATH=<runtime>/bin:$PATH`，`LD_LIBRARY_PATH=<runtime>/lib/python3.8/site-packages/torch/lib:<runtime>/lib`，`PYTHONPATH=$PWD:$PWD/rl_games`，`PYTHONNOUSERSITE=1`、`OMP_NUM_THREADS=4`、`MKL_NUM_THREADS=4`。H200远端无可用渲染通道，使用`--no-video`；完整MP4使用本地4090渲染。跨GPU有接触数值差异，不以退出码替代任务评分。

`singlepush-evidence.tar.gz`含本轮原始trace、240Hz法向接触、隔离标定、候选失败、几何证书、冻结验证和日志。MP4单独提供。源actor为既有update100，SHA256 `6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e`；其历史128env训练有容量警告，本轮没有新训练，也不以拟合结果声称能力。功能证据来自独立实际单env完整物理回放。

默认不运动的真机测力入口及具体单位/映射说明见HARDWARE-MEASUREMENT.md。所有真机实测字段为空，hardware_verified=false。私人附件、照片和旧刀媒体未发布。
