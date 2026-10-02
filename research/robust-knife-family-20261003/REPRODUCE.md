# G2 + Wuji v1 连续取刀与带阻力适配（进行中）

本轮从 `1c45ef574d068d56e800cf22c51e1fc8f2c0fe2b` 接续，实验副本单独工作。
真实刀柄主体输入为135×16×12mm（不含滑块），无按下解锁。主体/滑块质量、摩擦、阻力和执行器模型仍是仿真工程假设。

当前中心条件完整仿真demo已完成：v30从桌边拿取135×16×12mm刀，保持闭合，再连续两轮伸出/保持/缩回；变化新增负载和被动起动幅度各0.05N，原有25mm/8mm、10mm/.25rad与持续接触诊断均通过。拇指路径使用离线校准的连续滚动接触几何与原始有限增益电机目标；不是恒力控制，也不是学习策略成功。v31新增三角形变化负载/起动各0.10N并降低摩擦、v32附近联合几何变化同样通过。v33将同一参考接入合法2076/154维策略接口，以零学习修正再次通过中心条件。v34–v36还通过了尺寸两端和小幅摆放联合变化（均开发检查）。v37接入真正训练过的P50残差，在中心条件完整连续成功；参考控制仍承担主体运动，不据此宣称学习收益。完整必要泛化和独立检查尚未完成。

原始R800、普通残差和离线行为克隆在实际接管仍存在掉刀、转动或缩回失败。O1离线动作拟合误差小，但v29实际运行刀身转动2.56rad且未缩回，不能当作完成demo的学习权重。C100、E/F、G/H、I/J、K/L、M/N均保留为正常联合随机化/机制对照与失败证据；预置持刀检查与完整G2流程分开记录。旧固定材料点IK在27mm附近跳变约.928rad；新的41点连续滚动路径每1mm关节变化≤.04rad，实际最大刀身转动约.103rad。

## 恢复运行

需要 Isaac Gym Preview4、ArtGym Python环境（本轮torch2.1/cu118），并恢复以下原始权重。

- `runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth` SHA256 `bbf61592721300b1cf053de8246898a69989ed102b7a034da6fb47cc9a541dcd`
- `runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth` SHA256 `2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8`

权重由本轮最终Release提供；目前也可按上一轮Release及其freeze.json按需恢复。设置 `PYTHONPATH=.:rl_games`、`LD_LIBRARY_PATH=<artgym-environment>/lib`、`PYTHONNOUSERSITE=1`。仿真模块必须先导入Isaac Gym再导入torch。

连续取刀—接管尝试，输出目录必须不存在：

```bash
python -m scripts.run_g2_robust_demo   --output runs/robust-knife-family-20261003/demo/recovered-continuous   --video --seconds 36 --dx=-.10 --dy=.05 --yaw=45 --slider-face down   --grasp-plan research/robust-knife-family-20261003/pinch-equilibrium-bounded-v2/motor-plan.json   --table-calibration research/robust-knife-family-20261003/g2-cartesian-calibration-v1.json   --cartesian-path research/robust-knife-family-20261003/g2-cartesian-path-v1.json
```

最新带阻力接触诊断失败例（需要C100权重，SHA256见report与开发配对文件）：

```bash
python -m scripts.run_g2_robust_demo \
  --output runs/robust-knife-family-20261003/demo/recovered-contact-failure \
  --video --seconds 36 --dx=-.192 --dy=.05 --yaw=90 --slider-face up \
  --grasp-plan research/robust-knife-family-20261003/functional-edge-equilibrium-v1/motor-plan.json \
  --table-calibration research/robust-knife-family-20261003/functional-edge-self-localization-v2.json \
  --acquisition-path research/robust-knife-family-20261003/functional-edge-lateral-path-v1/acquisition-path.json \
  --residual-checkpoint runs/robust-knife-family-20261003/train/stability-C1/update_000100.pth \
  --thumb-action-gain .35 --load .05 --detent .05 --variable-load
```

这里刀位于明确配置的桌边，刀具重心在桌面内。不是任意桌面位置取刀能力。新增起动/有限势阱和变化阻力均为工程假设；滑块没有电机驱动。`knife-contact-pairs.jsonl`与`contact-schema.json`记录仿真接触对，仅供评估，不进入actor。端点条件通过而刀身失稳、拇指接触丢失，不算有效伸出或完整demo。

`--grasp-only --seconds 18`只验证拿取/保持。桌面位姿文件来自独立记录的仿真自然落稳状态，是一次性的理想离线校准；不是已接通相机，也不是运行时物体真值。过程中不重置物体，不固定刀体，不驱动滑块；动作和阶段切换只用预定时序、实际关节/FK、已发目标及真实50帧控制历史。

R800兼容性检查：

```bash
python -m scripts.audit_g2_r800_bridge --output runs/robust-knife-family-20261003/checks/recovered-parity
```

原始检查的2076维编码输入、合法actor观察和电机目标相符；证据 `runs/robust-knife-family-20261003/checks/g2-r800-bridge-v1/`。

联合尺寸/接触/阻力适配的正常基线训练：

```bash
python -m scripts.train_wuji_robust_residual   --output runs/robust-knife-family-20261003/train/recovered-A   --envs 1024 --updates 400 --randomization-scale .5   --load-max .10 --detent-max .10 --seed 2026100307
```

每50更新保存模型、Adam和RNG。`--resume <checkpoint>`恢复优化器，`--updates`是绝对更新数；物理回合重新开始，不是求解器逐位恢复。训练是预置功能抓姿的代理子模块；含四个来源，12个尺寸实例及连续随机接触、起动/变化阻力、观测/控制延迟扰动。`family-manifest.json`保存生成种子、来源及每个资产/抓姿哈希；独立4个尺寸实例目前尚未打开。

A/B/C/D历史训练pin在重置后的最初50帧继承补齐历史，其开发评估和G2部署均实际收集50帧。新的训练默认先中性保持50个真实控制步，再启用冻结actor与残差；保持步不计算actor梯度。`checks/actual-history-v1/report.json`验证首次actor调用为第50步、历史逐元素误差0。使用`--actual-hold-history 0`仅能复现旧pilot，不能作为当前部署历史规则。

当前实际取刀来源训练（E1；F1改support scale为1.0，其他参数相同）：

```bash
python -m scripts.train_wuji_robust_residual \
  --output runs/robust-knife-family-20261003/train/recovered-acquired-E \
  --envs 2048 --updates 1200 --seed 2026100322 \
  --randomization-scale .5 --load-max .1 --detent-max .1 \
  --support-residual-scale .25 --rotation-cost 4. \
  --object knife_wuji_acquired_family_20261003 --actual-hold-history 50 \
  --wrist-nominal research/robust-knife-family-20261003/acquired-family-v1/wrist.json \
  --wrist-probability 1.
```

实际取刀来源和四个既有功能来源各占50%。资产尺寸仍同一12/4分组，独立初始扰动重新生成。静态训练缓存初始化会清零速度；记录的连续取刀轨迹不会清零，所以二者必须单独验证。可选`--thumb-slider-reward`仅将仿真拇指碰撞网格到滑块包围尺寸的近邻代理加入reward，结合接触门控；它不是精确接触对力，也不进入154维actor。

```bash
python -m scripts.evaluate_wuji_robust_residual   --output runs/robust-knife-family-20261003/dev/recovered-A   --checkpoint <checkpoint> --envs 96 --seed 2026100311   --randomization-scale .5 --load-max .10 --detent-max .10
```

不带checkpoint是冻结R800配对基线。开发评估不等于最终独立验证；`--heldout`用于新几何的独立检查，不能用于调参或挑选模型。所有初始尝试保留，先实际保持50帧，随后四段5秒命令；失败后不重置物理。最终报告和权重尚未冻结。

主要连续runner输出 `continuous.mp4`、`hand-closeup.mp4`、`trace.npz`、`plan.json`、`physics.json`、`report.json`。净接触力仅是诊断，不能冒充拇指与滑块接触对力。平衡计划中的牛顿数不是实测力或恒力闭环。0.10N是新增诊断负载上限的一种配置，不是实物阻力上界。

本轮接续状态以 `STATE.json`、`HANDOFF.md`、`DECISIONS.jsonl`为准；PID和利用率必须重新核实。本轮不向真机发动作，最低12小时工作尚未完成。

## 密集几何与接触位置机制（进行中）

12个尺寸是早期诊断队列。当前训练采用512个联合均匀采样几何：W14–18、T10–14、L130–140mm，滑块轴向±5mm、横向±1mm；每个仿真slot的碰撞形状固定，运行期按回合连续随机化接触、起动/变化阻力、关节与校准误差、延迟。4个独立几何保留，不用于选模。

```bash
python -m scripts.prepare_wuji_dense_family --count 512 --seed 2026100330
python -m scripts.train_wuji_robust_residual \
  --output runs/robust-knife-family-20261003/train/recovered-dense-pressure \
  --envs 2048 --updates 900 --seed 2026100334 \
  --resume runs/robust-knife-family-20261003/train/acquired-F1/update_000100.pth \
  --object knife_wuji_dense_acquired_20261003 --randomization-scale 1. \
  --load-max .1 --detent-max .1 --support-residual-scale 1. --rotation-cost 4. \
  --actual-hold-history 50 \
  --wrist-nominal research/robust-knife-family-20261003/acquired-family-v1/wrist.json \
  --wrist-probability 1. --thumb-slider-reward 1.5
```

G3与H3使用相同父模型、几何、种子和交互预算，唯一区别是上述reward系数0与1.5；机制比较必须与这个正常适配强基线配对。F100 SHA256为`6d4a2d4d22afd249a3f62b2de8607604879fcbf08c3db86f41a003264783cef2`。G1/H1的检查点恢复失败和G2/H2的同步检查失败已保留，成功启动的是G3/H3。

Release几何恢复包`dense-family-v1-assets-caches.tar.gz` SHA256 `4179c0f63cb634c0f9ac742bfbc933881b7a0b86ff314052e026ae2b1f69b9a1`。从仓库根目录解压，或用上面的生成命令重建。单个对象的质量/惯性采用明确的恒定密度工程假设。

新的实际长边取刀抓姿可按固定接管前15秒帧生成密集训练代理：

```bash
python -m scripts.prepare_wuji_acquisition_transfer \
  --trace runs/robust-knife-family-20261003/demo/g2-side-edge-pressure-headroom-v18/trace.npz \
  --name knife_wuji_dense_longside_20261003 \
  --output research/robust-knife-family-20261003/longside-family-v1 --seed 2026100341
```

保留此前抓姿占50%，新实际长边抓姿占50%，不按策略成功筛选。静态缓存清零初速度的局限仍适用；连续G2流程从不在接管时重置物体或速度。

## 新的带阻力取刀来源与实际末态扰动

`g2-under-support-static-preload-v25`已连续从桌面取刀并在新增变化负载0.05N、起动幅度0.05N下保持关闭滑块及拇指/三支撑指接触；仅取刀子模块成功。`v26`R800接管掉刀；`v27`按时序拇指IK第一次实际压紧推进约36mm，缩回失去支撑。`thumb-path-branch-jump-v1.json`指出旧固定材料点路径27mm附近存在关节分支跳变，不能以小接触点误差宣称连续关节轨迹。

```bash
python -m scripts.prepare_wuji_acquisition_transfer \
  --trace runs/robust-knife-family-20261003/demo/g2-under-support-static-preload-v25/trace.npz \
  --time 15 --name knife_wuji_dense_under_20261003 \
  --source-family knife_wuji_dense_longside_20261003 \
  --output research/robust-knife-family-20261003/under-family-v1 --seed 2026100348
python -m scripts.train_wuji_robust_residual \
  --output runs/robust-knife-family-20261003/train/recovered-under-dynamics \
  --envs 2048 --updates 500 --seed 2026100350 \
  --resume runs/robust-knife-family-20261003/train/acquired-F1/update_000100.pth \
  --object knife_wuji_dense_under_20261003 --randomization-scale 1. \
  --load-max .1 --detent-max .1 --support-residual-scale 2. --thumb-residual-scale 2. \
  --rotation-cost 4. --actual-hold-history 50 \
  --handover-profiles research/robust-knife-family-20261003/handover-dynamics-profiles-v1.json \
  --contact-progress-reward 4.
```

普通适配M与候选N唯一区别是`--contact-progress-reward`为0或4；同父权重、种子、分布、控制幅度与交互预算。2.0残差允许取消/反向冻结actor的饱和动作；最终动作仍[-1,1]，支撑目标跨度仍0.04rad、拇指递推步长仍0.025rad，原关节/力矩限制及电机Kp不变。新奖励仅用仿真数据计算，接触位置与持稳门控下的有界、带方向目标误差减小，不向actor传入当前真值。

150个真实仿真接管前样本提供三种取刀腕姿态和腕坐标中的相对物体速度。它们与功能抓姿池独立混合，25%清零、其余按实测样本幅度0.5–1.0缩放，是工程扰动包络；代理手仍固定，未精确复现实际腕加速度或手指初速度。连续G2入口保留完整真实物理状态。`initial-snapshot.npz`及`initial-materials.json`在任何策略动作前保存完整初态；8例新开发对照所有已保存初态字段逐位一致，初始保持8/8有效，但R800/F100的操作均未完成。

新资产恢复包`under-family-v1-assets-caches.tar.gz` SHA256 `5d2cdc194023949614c3873936783d92c1b0de10a0ca1652cc1f4b665e79a3f8`。实际命令与权重哈希以每个jobs身份文件、开发报告及最终freeze为准；上列500仅原计划绝对更新数，是否延长由行为检查决定。


## 已完成的中心连续流程与同一参考的联合适配

恢复v30的脚本/几何控制成功例：

```bash
python -m scripts.run_g2_robust_demo \
  --output runs/robust-knife-family-20261003/demo/recovered-rolling \
  --video --seconds 36 --dx=-.1985 --dy=.05 --yaw=0 \
  --grasp-plan research/robust-knife-family-20261003/functional-side-edge-under-support-equilibrium-v6/motor-plan.json \
  --table-calibration research/robust-knife-family-20261003/functional-side-edge-under-support-v6/localization.json \
  --acquisition-path research/robust-knife-family-20261003/functional-side-edge-under-support-lateral-v3/acquisition-path.json \
  --handover-calibration research/robust-knife-family-20261003/handover-from-v25-v1.json \
  --thumb-script research/robust-knife-family-20261003/functional-side-edge-under-support-v6/continuous-thumb-v2.json \
  --load .05 --detent .05 --variable-load
```

v33使用同一运动参考的checkpoint接口，将上述`--thumb-script`替换为`--residual-checkpoint runs/robust-knife-family-20261003/train/geometric-reference-P0/geometric_reference.pth`。P0 SHA256 `39acf6ad7fb9b675e95c71bc0b02213db7a7ebba940f60ecc76915216afcea5b`，actor末层严格为0，继承父模型critic/隐藏层，不含新增拟合。冻结R800提供合法历史特征，几何参考负责原始目标，学习残差承担后续修正；不能将P0算作学习成功。`scheduled-reference-v30-equivalence-v1.json`验证600实际目标误差≤0.66µrad，`checks/geometric-reference-P0-bridge-v2/report.json`验证合法观察和电机接口。

参考在每次公开任务命令改变时启动四秒quintic轨迹，随后保持；仅读取已知任务、初始已发电机目标、当前已发目标与内部时钟。不同资产使用同一路径和同一checkpoint，`--knife-asset`只改变物理资产，actor仍使用登记的名义几何与固定离线校准。不会读取资产ID、当前物体/滑块/接触真值。

```bash
python -m scripts.train_wuji_robust_residual \
  --output runs/robust-knife-family-20261003/train/recovered-geometric-P \
  --envs 2048 --updates 300 --seed 2026100354 \
  --resume runs/robust-knife-family-20261003/train/geometric-reference-P0/geometric_reference.pth \
  --base-mode geometric \
  --thumb-reference research/robust-knife-family-20261003/functional-side-edge-under-support-v6/continuous-thumb-v2.json \
  --object knife_wuji_dense_under_20261003 --randomization-scale 1. \
  --load-max .1 --detent-max .1 --support-residual-scale .25 --thumb-residual-scale .25 \
  --rotation-cost 4. --actual-hold-history 50 \
  --handover-profiles research/robust-knife-family-20261003/handover-dynamics-profiles-v1.json \
  --contact-progress-reward 0
```

Q1仅将最后的reward系数改为4，其他初始checkpoint、种子、分布与交互预算一致；还未证明机制优势。154维可部署actor特征保持不变。几何参考每步根据已发目标计算动作，拇指学习修正不是无界积累；所有最终动作/电机目标保留原始限制。`--load-profile triangular|pulse|constant|sinusoidal|mixed`与`--load-frequency`用于登记的新阻力条件，默认sinusoidal/1.7保持旧模型。mixed为每回合固定类别，profile和阻力均不输入actor。

连续runner新增物理几何、摩擦、变化负载、关节观测噪声/偏置的显式参数。脚本或零残差模式对观测噪声通过不等于学得噪声鲁棒性。初始校准是仿真离线理想先验，未接真实视觉或触觉。`--load .1`是工程新增量，不是实物总阻力上限。独立资产012–015保持关闭，后续候选冻结后才检查。

## 实际 G2 完整场景训练

`G2ContinuousScene`使用完整27自由度G2+Wuji机器人、桌面和被动刀；前16秒连续接近、闭合、抬起、保持，后20秒由同一参考加有界残差操作。不会在接管时重置位姿或速度。512个训练几何重复到1024个环境，逐回合随机化真实摆放、摩擦、负载、初始校准、关节偏置/噪声与一控制步延迟。只有新训练回合开始时重置，掉刀的回合计失败。actor始终接收实际关节/FK、实采50帧历史、已发目标及固定名义几何/一次离线校准。

批量场景桥接先用非零P50权重与独立单G2入口比较：2076编码/134个测量与已知字段误差1.8e-7，最终电机目标误差2.4e-7rad。相同模型和相同输入在batch1下输出完全相同；冻结actor原始20维均值因batch8计算核差异约2.5e-4，原严格154维门槛仍记失败。补充的deployable门槛检查已知/测量字段、相同输入模型语义以及最终电机目标，不能称全部154维逐位一致。证据`checks/direct-G2-learned-P50-v8/bridge-parity.json`。八个名义完整物理回合全部完成，属于开发兼容检查。

```bash
python -m scripts.check_g2_continuous_scene \
  --output runs/robust-knife-family-20261003/checks/recovered-direct-bridge \
  --envs 8 --nominal --compatibility-gate deployable \
  --checkpoint runs/robust-knife-family-20261003/train/geometric-P1/update_000050.pth
python -m scripts.train_wuji_robust_residual \
  --output runs/robust-knife-family-20261003/train/recovered-direct-G2-P \
  --scene g2 --envs 1024 --updates 200 --seed 2026100357 \
  --resume runs/robust-knife-family-20261003/train/geometric-P1/update_000050.pth \
  --base-mode geometric \
  --thumb-reference research/robust-knife-family-20261003/functional-side-edge-under-support-v6/continuous-thumb-v2.json \
  --randomization-scale 1 --load-max .1 --detent-max .1 \
  --support-residual-scale .25 --thumb-residual-scale .25 \
  --rotation-cost 4 --actual-hold-history 50 --contact-progress-reward 0
```

P1/Q1均已从P50完成150个新增更新，到绝对update200，各4,915,200个新增真实G2交互。训练拟合不能替代冻结评估。实际G2训练固定sinusoidal/1.7工程负载，新的其他profile接口目前属于代理环境和完整单G2runner；不能把未传入实际训练的profile算作已覆盖。直接场景的接触奖励/训练诊断是网格近邻加净接触代理，部署runner另有接触对记录。


## 当前开发评估与压力协调分支（尚未最终冻结）

P50 learned hybrid在名义TABLE完整流程成功（v37），同权重在新增pulse/startup幅值0.2/0.2 N、低摩擦与观测噪声下也完成两轮伸缩（v38）。实际新增负载绝对最大0.459 N；幅值不是总阻力上限。0.5/0.5 N对照v39在18.2秒持续失去拇指滑块接触，刀身之后失稳并未缩回，实际新增负载最大0.964 N。原始力矩未饱和；原拇指base目标接近关节上限。`paired-capacity-figure-v2`使用原始接触对/负载/位姿轨迹，v1命令边界绘图已被修正。normal solver lambda为仿真法向接触贡献，不是实物恒力。

实际512训练几何联合开发检查：P50完整352/512，P200为359/512，Q200为350/512。保存初态全部字段一致，但GPU求解器前16秒轨迹仍存在数值差异；这些小数量差异不能归因于学习优势。严重旋转、掉刀和取刀失败是主要缺口。独立几何012–015尚未开启。

R1/S1从P200继续实际G2联合适配，2048环境，seed2026100359，绝对update1200为待行为反馈决定的计划；支撑/拇指有界残差比例0.75（原0.25），最终动作、关节/力矩/Kp限制不变。R负载/startup上限0.1/0.1、S为0.2/0.2 N工程幅值，contact-progress奖励均0。S400在与v39相同的完整TABLE较大阻力条件再次失败（v41），拇指18.2秒持续丢接触，不能声称训练突破容量。R400/S400的512联合检查用于决定后续训练价值，均属于开发评估。

新全手抓姿保留0.2rad拇指base几何余量，但初版v40实际取刀失败。补充完整抬升检查发现闲置无名指会扫入桌面边缘；原闭合位置和抬升终点检查漏掉此段，因而不能把v40失败单独归因为压紧不足。6mm抬升耦合压紧路径被拒绝，未运行。闲置手指停车、完整121点抬升证书及可选桌面约束静态力求解已实现；桌面约束静态力求解未找到可行解，输出保留但未执行。新几何/目标须分别通过路径检查、实际取刀、带阻力伸缩，不能以静态预测1.1N算作实测压力或成功。

所有启动、终止、源码pin、配置、权重及证据见DECISIONS.jsonl、STATE.json和jobs/*/{identity,execution,result}.json。阶段完成时恢复checkpoint包含Adam/RNG；中间检查不等于最终独立验证。个人照片/操作视频仅本地用于需求理解，其原文件不进入公开交付。
