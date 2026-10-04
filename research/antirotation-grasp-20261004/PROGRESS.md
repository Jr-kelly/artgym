# 当前开发进展（2026-10-04 00:07 UTC）

完整连续 demo、必要泛化尚未完成，未执行真机动作。本轮当前最强新成果是改变取刀预成形后，实际桌面侧向接近、闭合、抬起、保持成功；不是理想持刀 reset。

- 新布局：食指侧向，中指及小指刀底承托，拇指压滑块。原刀资产、真实手部网格、重力、执行器与被动阻力保留。
- 实际取刀：`runs/antirotation-grasp-20261004/pickup/opposed-table-strong-support-v3`；16 秒，抬起保持成功，静止拇指法向力约 0.797 N。尚未含伸缩。原几何保守 0.300 mm 桌隙检查为 false，最小网格分离 0.293767 mm；开发试验决定与原始检查均保留。
- 持刀子模块：`held/opposed-held-posture-high-load2-v3` 两轮约34 mm伸出、5.8/6.8 mm缩回，通过预先规定的新功能行为判断；原0.25 rad评分仍失败。0.5/0.5容量负载失败，不能当完整demo。
- 深入掌部布局加入食指对侧角支撑：相对手每轮累积转动由约0.278降到0.049 rad，回缩6.7/8.7 mm，第二轮仍未过原8 mm规则。只是子模块。
- 新 opposed 抓姿两组100更新2048环境短训（750初始化、随机初始化），采用八种物理训练刀和变化负载，均未解决较高负载回缩；已关闭，不原样延长。
- 实际取刀末态发生约8.8 mm/6.1°位姿变化。由上一条名义取刀记录生成一次离线操作参考；后续回合不读取实时刀/滑块真值。完整40 mm无预压触点几何已通过，固定初始偏置后半程与掌部相交，因此正在验证随姿态变化的目标。
- 控制桥新增可选0.12 rad支撑软件范围、每帧0.025 rad步长，原URDF限位/力矩/PD保留，已发动作历史保持实际目标。接口检查通过；已用于新实际取刀流程的动作范围/初始化短训对照；尚无训练收益声明。旧750真实记录600帧离线回归最大目标差0.60微弧度，30 Hz周期无超时；只是离线推理证据。

下一步：独立密集检查完整姿态预压路径，直接执行相同实际取刀前缀加两轮带阻力操作并录像；依据实际失败机制开展新流程联合随机化适配与必要泛化。远端4 H200已运行4组有用实际取刀适配，23:24:50Z当前整机均值58.75%，四小时门槛尚未满足或保证。

所有路径相对于实验副本，逐项原始证据和过程见 `events.jsonl`。最新已公开中间分支为 `feat/wuji-antirotation-grasp-20261004`，GitHub提交a529c815；尚无本轮正式Release。

## 新连续实测与正在执行的适配

`continuous/opposed-table-strong-2cycles-v4` 已完成36秒实际桌面取刀、两轮命令与双视角录像，无重置。实际拇指滑块子步接触100%，操作均值0.782 N、5%分位0.588 N；两轮伸出21.2/21.0 mm、缩回8.9/10.1 mm，**功能端点失败**，原完整分数失败。相对手转动最大0.310 rad，回缩到回缩增量0.063 rad/0.41 mm，最终保持稳定，除端点之外预先定义的行为项目通过。实际食指未形成侧向接触，不能仅凭名义几何称抗转动拓扑已实现。

原40 mm参考的固定目标插值与掌部相交已修复；新81目标参考+独立161插值原网格检查通过，速率仍由原每帧0.025 rad限制。`geometry-v10/actual-table-settled-index` 从已记录的实际名义取刀末态规划，角/侧接触均可达；选定角接触的有限目标与实际10 cm抬起后的12–14秒过渡路径通过，正验证全拇指行程，然后在同一实际取刀流程试验，不改变其他承托/拇指目标。

远端四组100更新、4096环境、八种训练物理刀、8秒开始学习实际抬刀的短训：span04-reset750、span12-reset750、span12-retain750、span12-fresh。仅训练拟合，尚未冻结评估或宣布泛化；与此前失败的理想持刀pilot不同。初始几何观察/关节偏置/延迟及变化被动负载保留，演员仅154维公开输入和冻结2076维R800，资产ID和接触真值仅物理加载/奖励。默认750离线推理回归已通过，0.12软件支撑目标独立步长/限位/已发历史检查通过。

## 切向轨迹与支撑耦合的新证据

四组实际流程短训已完成100更新，各26,214,400转移，可恢复模型/Adam/RNG与配置已拉回；第50更新各一次冻结名义检查均持刀/精确拇指接触100%，伸出仍约21 mm。保留750输出组回缩约5.3/5.6 mm，其他约7–8 mm。这是回缩开发收益，未解决必要泛化或完整demo，不原样延长。

离线几何发现：原零力触点路径40 mm，但Jacobian预压+碰撞投影后的虚拟电机指腹点只有19.1 mm轴向行程、额外7.7 mm向内位移。新增直接约束电机切向40 mm、允许有限法向退让的路径，41目标和161插值原网格/限位检查通过；深度/位置偏置从不作为恒力。`continuous/actual-table-direct-motor-2cycles-v7` 原承托在槽位阻力下脱落；`actual-table-direct-no-groove-v10` 同样非零0.2运行容量、仅去掉起动/槽位项作为诊断，完成两轮31.7/29.4 mm伸出、约8.0/8.1 mm回缩，接触100%，末次稳定，但原8 mm规则仍失败，不追0.1 mm小数。

`actual-table-direct-side-2cycles-v8` 在0.2/0.2容量下将第一轮提升到29.1 mm伸出/3.0 mm回缩，接触99.98%；第二轮21.0/2.5 mm，回缩到回缩累积0.286 rad，主要为刀长轴Z滚转，真实渐进滑移未解决。纯侧向支撑与完整电机轨迹有协同，但两轮全功能为false。原0.25rad标签并列保留。

正在检验实际侧面接触从靠中心高度移到靠刀底高度，增加长轴滚转力臂（1 mm到4.5 mm），方向仍纯侧向；目标0.8 N仅名义有限PD假设，其他承托和拇指目标保持，原碰撞/重力/力矩保留。几何/目标通过，实际12–14秒接触形成与两轮物理运行排队，不以几何通过宣称成功。当前12小时最早点仍2026-10-04 08:03 UTC，工作继续。


2026-10-04T00:36Z continuation:
- V12 rebuilt direct40mm motor path using the preceding V11 nominal settled frame, then passed independent161 original self/limit samples. Fresh actual table pickup/2cycles: extend29.42/21.81mm, return4.31/2.73mm, exact thumb substepcontact100%, relative max0.403rad, returnincrement0.181rad. Full demo remains false; no current truth enters controller. Videos and raw traces at runs/antirotation-grasp-20261004/continuous/actual-table-lower-side-calibrated-direct-2cycles-v12.
- New complete motor reference + actual lower lateral index12--14s transition were integrated into batched G2 prefix. Eight actual pickup nominal compatibility episodes all held the knife/full-or-nearly-fullcontact; different material baseline1/3 versus native.8/1.8, so no exact numerical parity claim.
- New contact-normal coordinates use initial known issued FK/estimated knife frame and explicit index side/middle+pinky bottom directions, no frozen support prior. Offline original FK inward direction, orthonormality, bounded targets/rate/history passed (controller-compatibility-v2/contact-normal.json). No policy performance evidence yet.
- Remote SSH failed twice with connection timeout around00:32Z; remote GPU/monitor current state unverified, no remote training running claim. Local4090 new actual-lower-side-fullmotor-joint-reset750-v2 pilot launched:4096env100updates, actor16s, unchanged original physical actuators/rail/criterion, new mechanical scene/fullpath. Actual instantaneous local utilization71--75% at00:35--00:37Z; cannot claim remote four-hour utilization.
- Two-stage common noisy initial observation IK generation started (32 observations/eight train geometries): separate actual pickup and lifted operation, preserve underside/ thumb targets across transition, adapt index side normal. Geometry certificates and actual contact not yet validated. Do not count as necessary generalization resolved.
- Next: review new pilot frozen50 behavior; compare contact-normal only on new actual mechanics if warranted; check representative initial-estimate geometry and actual pickup; publish source snapshot and eventually complete new Release. No automatic hardware motion.

## 2026-10-04T01:56Z continuation

V17 actual continuous tabletop pickup plus two loaded cycles passed the predeclared functional criterion using unchanged frozen750 on projected noisy nominal geometry. External command40mm; observed extensions32.21/26.44mm, returns6.49/1.99mm, pair thumb contact99.92%, return slip0.09546rad. This is a development simulation example, not literal40mm physical travel, independent generalization or hardware. Legacy0.25rad condition still false. Evidence runs/antirotation-grasp-20261004/continuous/actual-table-projected-grasp-frozen750-load2-v17.

Same frozen actor at.5/.5 holds the knife/contact but insufficient travel/return (V18); thick140x18x14mm case fails second extension/slip (V19). Original thin130x14x10mm geometry is rejected before physics for pinky/table hull conflict; bounded original-mesh motor projection now in progress. No collision, torque or pressure physics is relaxed.

Continuous one-path reverse motor preparation V20 improved actual returns to2.49/~0mm but lost second extension22.36mm. Separate forward/return joint blending failed85/405 original self-geometry samples and was rejected before physics. The main controller remains the original single-path implementation.

Two new-mechanics reset-head pilots closed without useful full-flow improvement (joint56updates and contact-normal50). A qualified nominal curriculum now retains the already functional frozen750 outputs,4096envs/50updates, original.04rad support span/.025support/.12thumb, new projected contact topology, random mixed nonzero resistance/material/sensor/delay. This is training fitting, not geometry generalization. Start01:50:32Z local child1151666; PID/GPU must be freshly checked when handing over. Batch compatibility first completed8 actual pickups/two cycles with matching actor input.

Remote SSH availability and current GPU state remain unverified after connection timeouts; no hidden/filler workload. Continue useful implementation/training/delivery until at least08:03:23Z. New GitHub Release still pending; latest published snapshot predates these results.

## 2026-10-04T02:34Z continuation

Published interim snapshot local801f042188190b0262ca8fcea81adc525e8fff1d/GitHubad9544ec918ddcb5363abead78c3d55fc8e2de12, exacttree2598b55b6d751881232f16f8b973151197899599. NewRelease pending; selected V17 development evidence now public, missing original pickup localization/acquisition dependencies will be added next snapshot/runtime package.

Retained750 nominal50 fitting V21 is negative: .5/.5 actual extensions24.55/23.60mm, returns18.83/15.26mm and return slip0.1155rad, worse than unchanged750 V18. Stop, retain optimizer/RNG checkpoint4c4f6d9ce644b1c787182357c450320db87c6f6742fc567c0081bac7704e64c7. New continuous reverse-prep/wristroll46mm virtual reference plus frozen750 V23 drops on .5/.5 first return; no continuation.

Thin geometry original open/touch/close conflicts were localized to pinky and middle. Generic bounded original robot/known table projection corrects both; complete actual acquisition73samples, transfer21 and full thumb161 original checks pass in initial-geometry-v5/thin-projected04-allcontacts. V24 actual pickup retains/free knife and100% slider contact, extensions25.32/21.96mm, returns5.61/6.28mm, bounded return drift0.06993rad; second extension fails. This is a traingeometry development case, not independentgen.

Same frozen750 matched8-environment nominal/thin/thick actual physical compatibility completes all pickups with no fall. A new three-geometry curriculum starts .1--.35 running/start passive capacities, mixed material/sensor/delay perturbations, original .04supportspan/.025support/.12thumb, retain750head, capped100 and actual frozen50 thin check. No unchanged extension of negative nominal.2--.6 fit. Scene/templates and physical schedules remain separate; actor154/no live object/contact/assetID.

Strict common necessary geometry bank16 preparation runs CPU pipeline1180631, started02:29Z; uses16 pre-existing noisy observations across8 train geometries, common self/table/fullstroke planner and original dense gates. Invalid targets excluded with evidence, no collision relaxation. Local utilization monitor1174078 heartbeat02:21Z; current metrics/PIDs must be rechecked, remoteSSH again timedout02:00Z/currentGPU unverified. GPU work is only actual useful training/probes, no filler. Continue until at least08:03:23Z unless actual documented external impossibility under Goal rules.
