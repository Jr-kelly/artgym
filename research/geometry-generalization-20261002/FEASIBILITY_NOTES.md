# 等待独立确认期间的可行性核查（未选分支、未启动新训练）

原 train_wuji_unified_student.py 的训练方法可复用，但固定 wuji_multigrasp/单资产/同源池，resume 会恢复旧 RNG 并覆盖 CLI optimizer LR。不要直接运行旧未发送方案。本轮目前只冻结评测，没有更新。

新证据：L110 独立64 F 全部来源都完成开合；student来源1全时段稳定33/64，teacher58/64；来源2反过来student61/64，teacher31/64。除严格精度外，确有 student 持握退化；teacher 不能充当来源2的可靠上界。完整screen W120来源3student F11/16、body0/16，teacher16/16、16/16；其独立确认仍待完成。宽/厚/长度抓姿来源3覆盖缺口另列，不能合并成一个根因。

候选 E→A：源3端部接触在长度适配中被clamp到刀柄内部。最多2个局部假设；一个是将初态中物体沿长轴平移半长度差，使负端接触保持原世界位置，再对拇指滑块接触做IK。保持资产中心/关节纵向锚点、质量惯量与动作不变，只调整合法抓姿；按几何端接触识别种子，不按policyID路由。尚未执行任何修复。

候选 E→C：若完整独立确认支持 teacher 在目标来源可靠、student新增功能/持握差距，可先做“2秒learner前缀→冻结teacher latent”的有限干预诊断。保留同一个actor与learner incomingRNN，以当前真实teacher privileged观测生成latent，替换encoder输出；显式标为有特权、不可部署的诊断，不能包装为student合法能力。它比更换为独立teacher RNN更贴近原蒸馏监督的反事实。同初态/F40s与冻结parent配对，目标L110来源1、W120来源3，保留teacher不可靠的来源2结果。先登记有用监督的判据；干预不改善则不盲目蒸馏。

若C诊断支持一次有界训练：
- 从SA51200恢复SC-real encoder和Adam，actor/normalizer/teacher encoder冻结，损失/结构/实际LR保持parent。新 wrapper复用旧训练核心，不能改变旧source路径。
- 几何/相应有效初态分布是主要变量；baseline继续蒸馏作同parent、同更新/交互预算对照。根据teacher可靠范围限制新几何采样，ID只用于环境资产/重置采样metadata，不进入policy。
- 可以用已经冻结筛查之前登记的screen-attempts中全部静态有效状态做训练（不只取policy成功者）；原screen数据于是成为candidate训练数据，不能作为candidate验证。不能训练独立确认或最终初态。创建新selection-dev种子，完整来源测试保留teacher差的来源。
- 多资产ArtManip已有lbx/pose-frame/env2instance；WujiGeometry会冻结每actor惯量，已取消multigrasp单实例限制。需一个小的资产选择hook，让初态来源与geometry一致。三角色baseline/L110/W120；baseline control三角色全部用原geometry，几何arm改变后两角色及合法初始化。保持同一学生encoder/actor处理全体条件。
- 原train在sample_grasps里固定source=slot%4。各slot的geometry只在建env时采样，reset从对应geometry/source的有效pool采样。teacher可靠新来源可取L110的0/1、W120的0/1/3，原geometry保留全4；source2新geometry不蒸馏不等于不评测。实际比例必须登记。
- 恢复RNG后只第一次显式初始化fresh optimization seed，之后interface_check的save/restore要正常保留RNG，不可每次重新播seed。读实际Adam LR/step，没有scheduler就写明没有。物理从新episode开始，不宣称bitwise PhysX接续。
- 第1窗口暂考虑+3200updates、save+1600/+3200（实际吞吐预检再定），每臂≤4GPUh。两臂同envs/rollout_steps、新交互/更新数严格相同，不用墙钟配平。主指标必须事先声明F已近饱和时的40s holding改善（建议新几何宏平均至少10pp，baseline function/holding回退不超约5pp），所有已覆盖来源仍展示；只loss更好不续行。
- 若有跨尺寸训练，冻结前登记至少1–2个没有训练/选模型的几何组合用于独立最终集，不只换随机种子。最终集打开后不能选择checkpoint或调整初始化。

只选择一个主要分支；这些是代码/预算可行性笔记，不是启动批准，不代表根因或改进已证实。实际执行决定须在完整screen和关键独立确认之后写入DECISIONS，仍受64累计预算与≥6GPUh预留约束。
