# 本轮复现与续接

先读本目录STATE/HANDOFF/REPORT/freeze.json。旧width、press最终结果及确认集保持关闭；本轮确认打开后同样关闭，不用于重选。源码分支feat/wuji-real-size-student-adaptation-20261002。实测33024端点有4张H200，本轮没有申请新资源或使用子代理。

Release证据包使用既有格式：

```bash
python -m scripts.restore_wuji_unified real-size-student-evidence-v1.tar.gz --output RESTORE_ROOT
```

包中含本轮照片/视频解码副本、资产、静态初态、配置、完整新增encoder/Adam/RNG checkpoint、原始轨迹与报告。未变的C3200/teacher继续使用既有width v1及父权重包，路径与SHA在STATE；不重新发布未变权重。环境沿用IsaacGym/TacSL、Python3.8.20、Torch2.1.0+cu118；先import IsaacGym。所有已执行命令及源码哈希在runs/real-size-student-adaptation-20261002/jobs/*/identity.json，退出与GPUh在result.json。

训练直接复用scripts.train_wuji_unified_student，加--real-size-adaptation选择登记的目标/锚点槽。内部width-arm G在本轮称R，不是旧宽度实验G；C/G-training.json明确实际几何和初态。其余loss/controller/horizon/learning-rate均保留。绝对updates终点与新增更新不同；首窗口54400→55200，各臂800次，每次256×4个transition。新实验共同fresh seed只用一次，续窗保留各自RNG/Adam。checkpoint恢复用--resume，续窗不再传--fresh-optimization-seed；模拟器从新episode reset，不声称恢复PhysX逐位轨迹。

单次评测模板（重现用，不自动重启）：

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=.:rl_games python -m scripts.evaluate_wuji_real_size \
 --states runs/real-size-student-adaptation-20261002/static/dev/valid-states.npy \
 --student-checkpoint CHECKPOINT_FROM_FREEZE \
 --output NEW_UNIQUE_OUTPUT
```

同目录selection.json记录来源。CPU复算保留轨迹使用：

```bash
PYTHONPATH=.:rl_games CUDA_VISIBLE_DEVICES='' python research/real-size-student-adaptation-20261002/analyze.py
```

视频为预登记dev首个来源3状态的RTX单状态相机重仿真，不能替代H200批量统计。局部video row0不是来源0。只有必要的独立新诊断才使用非零阻力/位置偏置；位置偏置不等于恒力。真实接触力、行程、质量/惯量没有实物标定。认证参数不进入发布包。
