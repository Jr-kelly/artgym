# 最短复现与续接

本轮已完成，无待执行训练。读取STATE/HANDOFF和REPORT；旧width/geometry最终集保持关闭。本轮确认集也已关闭，不再用于调参。已授权SSH仍为17314；认证只在私有环境中传入，不写入此包。

1. 克隆分支`feat/wuji-real-knife-press-resistance-20261002`并恢复本轮`real-knife-press-evidence-v1.tar.gz`：

```bash
python3 -m scripts.restore_wuji_unified real-knife-press-evidence-v1.tar.gz --output RESTORE_ROOT
```

2. 复用已有IsaacGym/TacSL环境（H200: Python3.8.20/Torch2.1.0+cu118）；先import IsaacGym。C3200和teacher沿用width v1/旧geometry父权重包，SHA见STATE。此轮不重新发布未变的大模型。

3. 如需复算结果，CPU NumPy/SciPy环境执行：

```bash
PYTHONPATH=.:rl_games CUDA_VISIBLE_DEVICES='' python research/real-knife-press-resistance-20261002/analyze_and_report.py
```

该脚本读取保存轨迹，复用原score_timed_trace、Wilson和paired_ci，不产生新GPU数据。报告生成会写本轮新工作副本的REPORT/STATE/日志；对下载的干净副本运行。

4. 实际单条件评测命令示例（复现用，不是自动重启）：

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=.:rl_games python -m scripts.evaluate_wuji_press \
 --states runs/real-knife-press-resistance-20261002/static/dev-repaired/valid-states.npy \
 --press-mm 0.5 --resistance-n 0.05 --profile variable --profile-seed 2026100233 \
 --output NEW_UNIQUE_OUTPUT
```

同目录selection.json提供来源映射。相机单行文件局部row0对应VIDEO.json登记的原来源3、dev row8，不能把局部索引当成来源0。视频是RTX单状态重仿真，独立于H200统计。

状态与版本：主矩阵/确认/视频源码哈希见freeze.json和作业收据；更早pilot只在诊断力投影中有坐标系错误，PILOT_SUMMARY和分析已从原始接触向量重算，未改policy/物理。零按压路径q/target/slider/物体/action与原路径在2e-6内一致。按压递推没有重复积累偏置，最终issued memory误差0。阻力每物理步逆相对关节速度施加，施加时功率非正，保持关节反作用。

无需重做环境/恢复/全量下载审计。下一轮优先解决近似实物厚刀的接触压紧与持刀支撑；新实验另登记，不在当前确认集寻找漂亮参数。
