# 闭合上下文有限配对：开发原型

这组实验由固定P50在厚刀柄的持续支撑失败、以及实际8秒测量历史的厚度辨识信号触发。它不更换冻结的主策略，不并入原332独立成绩。actor为原154维加一个缓存的厚度估计，共155维；critic为原181维加相同缓存量，共182维。主连续demo仍使用原P50与原生G2R800Policy。

入口 `context_conditioned_residual_experiment.py` 在8秒构造与已拟合数据同语义的194维输入：134维测量/已知公开量，加50帧归一化实际测量关节的均值、标准差及末首差。一次名义标定、已发目标和测量FK可以使用；运行时没有物体/滑块姿态、接触、阻力、材质或资产ID。监督标签只在冻结ridge10的409个训练族刀柄拟合时使用，103组为几何监督留出；这些刀柄已参加RL训练，因此不是整个策略独立验证。所有失败/未取稳数据保留。

估计在8秒捕获一次，转换成 `(T_est_mm-12)/2` 并限至±1.5；恒定对照提供0，即名义12mm。16秒开始残差动作，其余闭合、持稳、参考、执行器与原判据相同。缓存只在新物理回合开始时清除，阶段间不重置物理状态。位置参考/估计量不等于恒力。

初始checkpoint为原P50的零列扩展，保留已有参数、Adam与CPU/CUDA/NumPy RNG；新增actor/critic输入列和对应Adam矩为0，初始输出核对误差均0。输入重放在原保存测量上最大误差约4.2e−7。训练两组同种子，各固定新增300更新，只对末次update350作预登记固定512开发检查，不按中间计数选模。

解压主恢复包和单独的 `closing-context-adaptation-evidence.tar.gz` 到同一个新的根目录。需要本轮记录的IsaacGym/PyTorch环境，设置 `PYTHONPATH=.:rl_games`、`PYTHONUTF8=1`、`PYTHONNOUSERSITE=1`。从该根目录运行，例如继续AT已完成checkpoint至绝对351更新：

```bash
python research/robust-knife-family-20261003/context_conditioned_residual_experiment.py \
  --mode train --conditioning estimated \
  --output runs/robust-knife-family-20261003/train/context-AT-resumed \
  --envs 2048 --updates 351 --horizon 32 --seed 2026100502 \
  --randomization-scale 1 --load-profile mixed --load-max .1 --detent-max .1 \
  --epochs 4 --minibatch 4096 --scene g2 --base-mode geometric \
  --actual-hold-history 50 --support-residual-scale .25 --thumb-residual-scale .25 \
  --contact-progress-reward 0 --functional-thumb-reward --strong-slider-contact-reward \
  --absorbing-failure-penalty --active-kl-stop --bounded-actor-update \
  --takeover-seconds 16 \
  --resume runs/robust-knife-family-20261003/train/closing-context-AT-v1/update_000350.pth \
  --thumb-reference research/robust-knife-family-20261003/functional-side-edge-under-support-v6/continuous-thumb-v2.json
```

AU使用 `--conditioning constant` 和AU对应checkpoint。实际训练命令、初态、head与helper的精确哈希保留在预登记、jobs身份/执行/结果和证据包manifest。恢复Adam/RNG会建立新物理回合，不是恢复整个PhysX求解器状态。

固定末次开发检查示例（输出目录须不存在）：

```bash
python research/robust-knife-family-20261003/context_conditioned_residual_experiment.py \
  --mode check --conditioning estimated \
  --output runs/robust-knife-family-20261003/checks/context-AT-recovered \
  --envs 512 --seed 2026100503 --randomization-scale 1 \
  --load-profile mixed --load-frequency 1.7 --load-max .1 --detent-max .1 \
  --checkpoint runs/robust-knife-family-20261003/train/closing-context-AT-v1/update_000350.pth \
  --takeover-seconds 16 --compatibility-gate off
```

这里关闭的是原154维接口诊断入口，原物理成功判据保持。155维原型不能直接传给原生G2R800Policy，没有声称已接通该原型的原生部署或真机。配对同时向actor和critic提供上下文，不能孤立归因于actor；不同GPU的接触轨迹也非逐位相同。末次实际开发结果另见闭合比较报告，不以训练最近128个先结束回合统计代替开发检查。
