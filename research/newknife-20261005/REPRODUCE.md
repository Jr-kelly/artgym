# 新刀冻结候选复现

这是新刀最强失败候选的连续仿真交付。功能通过、必要泛化覆盖与真机就绪均不能因打包而改为成功。原始用户照片与附件不在交付包中。

## 运行

使用已安装 Isaac Gym 的兼容 Python，在恢复目录运行：

```bash
python -m scripts.run_wuji_newknife_selected --output runs/my-newknife
python -m scripts.run_wuji_newknife_selected --profile variable --no-video --output runs/my-newknife-variable
python -m scripts.run_wuji_newknife_heldout --case small-low --output runs/my-heldout-small
python -m scripts.run_wuji_newknife_heldout --case large-high --output runs/my-heldout-large
python -m scripts.run_wuji_newknife_heldout --case middle-variable --output runs/my-heldout-middle
```

每个输出必须是新目录。标称入口从真实桌缘取刀连续运行36秒，12–14.2秒已知电机路径换握，随后两轮35mm命令与保持/回收。轨迹和物理状态没有重置。泛化入口只用一次初始几何估计准备路径；保持同一冻结权重、原限制、统一recipe，拒绝的几何条件保留失败而不执行。

## 空目录恢复

复用 [既有依赖 Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-wrap-force-20261005-v1) 的两个归档：

- wrap-runtime.tar.gz，SHA256 `3641e30850d88a41a5db4c385ff06d50ca321bc1f47e6527cd23fdcbd1a43fab`
- wrap-learning-state.tar.gz，SHA256 `519d9dc52d7cb1091da79901268933e8ccabfa908425bd1b1ccdc98ec84039b4`

本轮 newknife-overlay.tar.gz 包含冻结权重、新资产、所有已哈希运行依赖和共同几何recipe输入，不需要旧 highload/traction覆盖包。

```bash
python -m scripts.restore_wuji_newknife --baseline-dir /path/to/wrap-archives --overlay /path/to/newknife-overlay.tar.gz --destination /path/to/new-empty-directory --run
```

恢复器校验依赖哈希与逐文件哈希，真实运行完整36秒，保存 RESTORE-RESULT.json。此检查证明同机可恢复性，不是独立泛化，也不将成功退出码当成动作成功。最终完整任务评分见其中 evaluation。

Isaac Gym授权runtime另行安装。已验证 Python3.8/Torch1.13/IsaacGym本地兼容环境；PATH设runtime/bin，LD_LIBRARY_PATH先torch/lib再runtime/lib，PYTHONPATH设恢复根目录及rl_games，PYTHONNOUSERSITE=1，OMP_NUM_THREADS=4，MKL_NUM_THREADS=4。仿真先导入Isaac Gym再导入torch。跨GPU接触轨迹允许数值差异；任务判据不变。

## 证据边界

newknife-evidence.tar.gz保存开发比较、所有训练日志/配置、冻结验证、逐240Hz接触记录、轨迹及利用率。128env新抓姿训练曾报告GPU broadphase容量不足，拟合可能漏交互，不能用它主张物理成功。选型依赖的8个单env原生完整回放无该警告。FROZEN-CANDIDATE.json固定权重、控制源码、recipe及资产哈希。

75gf=0.73549875N是用户轴向参考量级，固定夹具加载运动响应为仿真校准证据，恒容量及变化曲线是明确假设。法向力、轴向总力缺测、制动容量和位移分别报告。没有真实机器人运行结果。
