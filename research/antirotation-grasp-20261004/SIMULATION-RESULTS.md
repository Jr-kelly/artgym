# Actual continuous antirotation development results

The frozen750 policy with common initial noisy-geometry IK, bounded original
self-geometry motor projection, a lower index side contact and a full tangential
thumb motor reference completed actual tabletop pickup followed by two loaded
extend/hold/retract/hold cycles in V17. This is one nominal development example.
Necessary geometry/load generalization and real hardware remain unresolved.

The external command is40mm. The measured V17 extensions are32.21/26.44mm and
returns6.49/1.99mm. This passes the functional criterion declared before the
experiments; it does not demonstrate literal40mm measured physical travel. The
legacy0.25rad world-pose criterion remains false and is reported unchanged.
No body attachment, runtime object state reset, rail positive assistance,
collision simplification, reduced gravity or increased actuator limits is used.

| Development trial | Controller/mechanics | Resistance capacity run/start N | Extension mm | Return endpoint from simulated lower limit mm | Finding |
|---|---|---|---|---|---|
|V17|Frozen750, projected noisy nominal/lower index|.2/.2|32.21/26.44|6.49/1.99|All predeclared functional checks pass|
|V18|Same V17 actor and geometry|.5/.5|23.73/22.69|16.86/12.12|Continuous contact/holding; inadequate traction/return|
|V19|Same actor, noisy140x18x14mm estimate|.2/.2|28.94/21.47|4.17/2.75|Second extension and progressive return slip fail|
|V21|Retained750 nominal50 fit|.5/.5|24.55/23.60|18.83/15.26|No return improvement; fit stopped|
|V23|Prepared continuous wristroll plus frozen750|.5/.5|22.63/20.56|20.56/20.56|Drops first return|
|V24|Thin original full-acquisition geometry repaired, frozen750|.2/.2|25.32/21.96|5.61/6.28|No fall/contact retained; second extension fails|
|V25|Same thin path, three-geometry fitted50|.2/.2|25.81/22.27|6.73/6.50|No meaningful improvement; safely stopped at54|
|V14|Projected nominal scripted motor reference|.5/.5|24.20/20.47|20.47/20.47|Knife dropped during first return|
|V20|Scripted continuous negative6mm tangential preparation plus known wrist roll|.2/.2|31.64/22.36|2.49/~0|Improved reversal, insufficient second extension/support displacement|

Solver brake values above are passive capacities in addition to actual contact
friction, not measured real cutter resistance or a real-world upper bound.
V20 changes virtual motor travel to46mm while external rail command remains40mm;
virtual preload/position offsets do not constitute constant physical pressure.

V17 exact pair-contact fraction99.9168%; relative maximum rotation0.28625rad,
return-to-return incremental rotation0.09546rad, translation0.876mm, final
angular velocity0.00631rad/s. Videos are continuous.mp4 and hand-closeup.mp4
inside runs/antirotation-grasp-20261004/continuous/actual-table-projected-grasp-frozen750-load2-v17.
Frozen750 SHA256:11f87269e7910380c6dab1fa8dcc26e53e40da0bd905a1ae40e7ffcf812b1a1d.

The exact direct run command is in the corresponding jobs/*/identity.json;
run its command with a fresh --output directory under the experiment clone.
Research helpers reproduce derivations in order and intentionally reject an
existing output rather than overwriting historical results. The dependency
configuration paths are included in the recoverable Git snapshot; larger
weights, traces and videos will be delivered as Release assets.

Separate forward/return motor-reference blending was rejected before physical
execution:85/405 intermediate samples failed original self geometry. The
controller was restored to the single-reference implementation. Thin130x14x10mm
geometry initially failed table clearance at pinky link4/pad; first touch/close
repair passed dense closing/transfer but full open approach still failed.
The revised repair covers all open/touch/close targets. These are geometric
preparation checks, not successful physical generalization.

Two reset-head new-mechanics training pilots closed without functional behavior
improvement; their frozen evaluations and optimizer/RNG checkpoints are retained.
The nominal50 and three-geometry54 pilots are closed negative training
fitting results. No success rate from training or development is labeled independent
validation, and no hardware result is claimed.

Isolated source/dependency recovery completed the full V17 run with identical
trace SHA. A large frozen-policy population probe reproduces training-scene
pathology before optimization; further unchanged PPO is suspended while checking
physical batch validity. This recovery/diagnosis is separate from necessary
generalization and from real hardware.


V26 薄刀柄加入既有食指承托保持控制：伸出24.69/21.42mm、回缩1.80/2.77mm，第二伸出和循环转动漂移失败。V27 加入既有法向力矩分配控制：第一伸出29.53mm，第一次回缩即掉落，接触覆盖约37.5%。这两条负结果说明改善回缩端点本身不足以保持完整功能抓姿；不据此断言单一因果，也不延长或微调同一失败方案。

2026-10-04T05:30Z，必要高度/偏置范围已完成原始几何检查准备。四个滑块高度2–4mm变体、每个两次带噪声初始估计，以及四个预先登记的新联合条件均保留完整检查与拒绝记录。关节投影的快速路径原来只检查自碰撞而遗漏既有5mrad关节余量，修复后重新准备两项原拒绝目标；物理关节、碰撞和评估条件没有放宽。该准备尚不证明高度泛化。


|首次高度开发例|真实仿真形态|伸出mm|回缩末距仿真下限mm|结果|
|---|---|---|---|---|
|b0|135×16×12、凸起2mm、轴向+5/横向−1mm|22.02/2.91|1.61/2.09|行程、接触、循环漂移失败|
|b1|135×16×12、凸起4mm、轴向−5/横向+1mm|36.16/31.54|6.79/3.87|全部预先功能判据通过，旧评分仍失败|
|b2|130×14×10、凸起4mm|27.51/25.57|9.38/11.53|回缩与循环漂移失败|
|b3|140×18×14、凸起2mm|22.14/17.07|1.39/约0|伸出行程失败|

四例均为同一750、统一带噪声初始估计/目标适配、.2/.2 N容量，固定使用每个形态的第一组初始观测，不按行为结果挑样本。全部实际取刀、36s两轮视频/接触记录保留；属于已知训练形态的开发行为，不用1/4估算泛化可靠性。b1恰好能通过，不取消其余必要范围或高阻力剩余目标。详细真实尺寸、初始估计、哈希和判据见HEIGHT-DEVELOPMENT-RESULTS.json与原始physics/report/functional-evaluation文件。


新5秒接管、正确桌面初始坐标训练两组各50更新已冻结。range04 名义/薄刀柄均失败；薄刀柄两次伸出36.02/36.27mm，但第二回缩末9.27mm、循环转动0.185rad及末次持稳失败。range12 名义/薄刀柄也失败，第二伸出均不足25mm。未延长或扫增益。按预先登记规则，两候选不合格，冻结原750再打开四个新联合条件。四例首次实际连续验证全部保留，0/4功能通过：第二伸出不足、第二回缩末超限或循环转动漂移。不能用这四例估计宽范围成功率，也不按其结果重选策略。详见FRESH-JOINT-ACTOR-FREEZE.json和FRESH-JOINT-VALIDATION-RESULTS.json。

无名指对侧下缘新支点 V36 几何全行程通过，但实际刀柄接触约22%，回缩末18.11/21.10mm；有限关节跟踪滞后搜索 V37 达到+0.0195rad目标偏置，实际接触约38%，承托法向约0.024N，仍有2.2秒拇指零接触。V37伸出22.74/11.56mm、回缩末10.61/8.75mm、循环转动0.330rad，失败后停止。关节滞后不是牛顿力或接触归属；V37也改变过渡时序，不作单因素因果结论。原视频、轨迹和精确计划保留。

表中伸出/回缩数值均为距仿真导轨下限的末位置，不是每段运动距离。功能端点规则不意味着两段各走满40mm、真实刀片完全伸出/收起或全必要范围达成；原40mm指令和原评分均保留。

必要24模板/12形态的保留750关键对照，各1536×512×25更新已结束：frozen-thumb名义末位置33.09/28.11、回缩7.34/2.92mm，循环转动0.141rad失败；薄26.04/22.19、回缩7.41/6.32mm，第二伸出失败；高度35.60/29.05、回缩7.14/4.54mm功能通过。整手共同学习名义与薄同样失败，高度首次回缩末8.28mm超限。已有高度750成功，不能把这一次差异包装成普适新收益。两组未过整体门槛，均止于25，不继续扫阈值或重复训练；六条实际连续视频、权重/优化器/RNG和逐项原判据见NECESSARY24-FROZEN25-RESULTS.json。
