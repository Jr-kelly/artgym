# 本轮进行中的复现入口

从前轮Release `wuji-g2-support-pressure-20261003-v1` 与分支提交 `d0d6ce01d5550ec5b512fdc4e510c5546569d8b4`接续。新工作分支`feat/wuji-antirotation-grasp-20261004`，本地实验根目录见HANDOFF；旧大型权重/资产依赖复用，尚未发布本轮最终Release。只运行本轮有用计算，不执行真机动作。

任务Python：本地`/home/agiuser/miniconda3/envs/artgym/bin/python`；远端`/home/wangjiarui/artgym-runtime/bin/python`。科学进程需`PYTHONPATH=.:rl_games PYTHONNOUSERSITE=1`及对应runtime库；SSH/rsync/GitHub命令清除`LD_LIBRARY_PATH`。Host Python不提供NumPy/SciPy/Torch，不能用于科学规划。

主要源码入口：
- `scripts/plan_wuji_antirotation_grasp.py`：结构不同的deep/opposed/rolled/bilateral，完整40mm两端、原网格碰撞与关节余量。几何通过不能计为物理成功。
- `scripts/run_g2_robust_demo.py --held-diagnostic`：显式预置持刀子模块。初态为几何touch_q，原有限PD形成压力，刀完全自由、有重力；不计连续demo。
- `scripts/run_g2_robust_demo.py --postlift-regrasp path.json`：实际旧取刀后、已知时钟的机械臂和手目标过渡；不写物理状态或清历史。第一低预压过渡未持住，失败保留。
- `scripts/plan_wuji_postlift_regrasp.py`：一次离线估计和G2 FK生成过渡，检查臂速度/桌面及抽样手碰撞；接触连续性只由物理试验判断。
- `scripts/evaluate_wuji_antirotation.py`：预先声明的新行为判断与相对手曲线，原0.25 rad评分并列保留。
- `scripts/prepare_wuji_normal_preload.py`：简单法向阻抗假设，不能冒充静力平衡或恒力；后接已有姿态预压/原目标检查。
- `scripts/replay_wuji_support_commands.py --prewarm-iterations 8`：真实50帧历史后隔离完整计算预热，恢复控制状态，零下发。
- `scripts/fit_wuji_passive_resistance.py`：双向实物CSV入口；当前仅合成例，原始值与被动模型图，不算实物标定。

有价值开发例为`runs/antirotation-grasp-20261004/held/opposed-held-posture-high-load2-v3/`：两轮端点通过、接触100%、回缩后稳定；原0.25rad评分失败，新功能判据通过。它仍是持刀诊断，不是桌面完整demo。0.5/0.5容量例、低预压例及首次连续换握都保留失败，不计入泛化成功。

每项完整命令、PID/时间、退出状态保存在`runs/antirotation-grasp-20261004/jobs/`与remote-manifests，决策在本目录events/STATE/HANDOFF。远端worker为独立实际试验，不依赖聊天进程；结束后拉回结果，并更新父journal。后续最终交付会给选定配置、权重和一个可恢复单入口，不能把当前实验索引当作完成声明。
