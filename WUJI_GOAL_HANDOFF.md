
## Overnight G2 20260926 2026-09-25T21:52:25.768004+00:00

R3-01第二10度转腕通过，末三指100%、固定世界4.678mm/0.22617rad；接近旋转上限，停止直接叠加。R3-03开始一次物体真值朝向驱动的腕部小校正，回到原gait开始即固定的世界目标；手指命令不动，原0.25rad/5mm控制准入界限及评分不变，补齐IK全路径自身碰撞检查。R3-02四指平移仍运行。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T21:50:07.449888+00:00

R3-02开始：完整R2-16连续前缀后，保留拇指/中指/无名指/小指四个实际接触并平移10mm。45路径采样无新增自碰/臂掌碰桌，材料点误差0.693mm、指令峰值0.146rad/s。食指前段目标两分支拒绝，无额外物理。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T21:46:25.418132+00:00

R2-16支撑通过但去拇指静力仍无解；接触集中刀尾，正在检查食指前段底部支撑。R3-01开始独立备选：R2-14连续前缀上保留拇指夹持，再向功能方向转10度，45采样通过；不是小指支撑后的释放。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T21:44:45.973943+00:00

第二轮结束：R2-16新增小指底部支撑通过，末1秒四支持指100%接触、固定世界4.282mm/0.145498rad。R2-14实现候选2名义12mm平移+10度旋转，但当前直接拇指触滑块两种表面分支未过几何。第三轮先检验实测小指能否替代拇指支撑，再继续功能姿态接近；不把G1/几何成功当整段。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T21:40:24.807810+00:00

续接实查原训练88339存活；R2-14保持夹持转10度末1秒通过，R2-15独立A端点通过但旋转0.265058rad超稳定门禁。R2-16已启动小指从下方绕行建立第四支撑，保留其余三个电机参考。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T21:27:45.608908+00:00

R2-13通过累计名义12mm平移：仍由拇指/中指/无名指100%接触，末1秒固定世界4.143mm/.083551rad，小指0接触；实际刀心误差进一步降至约36.73mm。实测小指间隙3.904mm，不称4.1mm已离触，但该小指没有有效接触。根据真实末态，保持对向夹持的10度功能轴转腕几何通过，正在采样审计后执行。备选食指两关节的0.2mm表面接触迁移网格也未连通，未启动物理，不把该离散失败当四关节不可达。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T21:19:34.632088+00:00

05:19方向复核：A功能终点+实际接管已通过，几何近似A55未能接管；拇指离触后的长轴/功能轴开环都在第二小段失去食指并旋转越界，停止继续延长这些开环路径。R2-12候选2保持拇指夹持的4mm腕部平移通过，实际手内刀心误差46.49→42.60mm，有真实位置改善、非刀随腕整体平移；据新的实际接触再规划下一短段。将主优先级转向候选2先修正手内位置，再建立非拇指支撑/释放；不新增获取候选。小指三支撑下食指避碰路径作为有界备选。学习仍未启动：优先完成已有有进展的控制路线，未建立可信局部学习环境/评价冒烟。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T21:14:35.372304+00:00

R2-10功能抓姿A通过实际2秒停稳后冻结teacher：600操作步，两轮各段端点0.815/0/0.240/0mm，世界4.520mm/.226606rad，2mm与稳定通过；仅独立A，不是连续获取。R2-09此前75维缓存未转70维候选格式，首次物理步前拒绝，错误保留。R2-08四支撑目标失败，但实际小指接触100%、食指0%，中指/无名指/小指三支持1秒、世界3.354mm/.21109rad、拇指>=4.237mm；新接触替换了食指，不能写四指成功。R2-11功能旋转轴10度在途，R2-12复用候选2前缀只做4mm持刀腕部平移；10mm提案在6mm几何拒绝，前4mm采样自碰/臂掌均通过。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T21:03:13.970994+00:00

R2-07结束：前1890帧与R2-03完全一致。腕部校正把固定世界旋转误差降到.08218rad，但食指末1秒0接触、拇指间隙3.954mm，三支撑/离触门禁未通过；无掉落、未进策略。功能角差反而103.67→107.04度，不能把世界对齐当手内进展。R2-09已启动已知功能抓姿A的2秒实际停稳/真实参考接管正对照，用于核查新候选A接口；R2-08小指支撑在途。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T20:57:44.364718+00:00

R2-08启动：相同15度连续反馈前缀后，只移动小指到刀体右侧z=-39.2mm，先无碰触及再1mm有限驱动闭合，1秒要求四指接触与全拇指离触。两段采样无小指自碰撞，预压只是命令。另发现当前到功能抓姿旋转轴[.262,.374,-.890]，不等于刀长轴；已新增显式轴选项，10度短段和60度几何屏正在跑。A55局部腕部两分支终点搜索均未过几何，暂不追逐该未验证操作终点。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T20:52:22.591737+00:00

R2-07已启动连续15度反馈前缀后的一次固定目标腕部校正：停止残差更新但保留最后真实电机命令，支撑指固定；检验能否保留三接触并恢复原世界姿态裕量。A55真实末态两个拇指几何分支均失败，未浪费物理补偿试验。另在几何阶段有界搜索保留中指/无名指支撑的腕位移终点。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T20:49:30.392504+00:00

R2-06独立A55末1秒两指稳定，但拇指/食指无接触，未通过接管门禁、未进入teacher；漂移0.0054mm/.000110rad，拇指间隙2.059mm。实际停稳相对预置转动.14458rad，下一步据真实末态检查一次拇指接触补偿，不把A当获取。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T20:48:19.369487+00:00

R2-06独立A55已启动：几何候选首次物理步前加载、2秒真实停稳，仅握持通过才接冻结teacher。新增接口明确候选滑块初态、实际历史与最后电机目标；不用于B重置。实查旧训练88339活跃，GPU88%，远端90871d7与本地一致。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T20:41:37.066814+00:00

R2-05第二段反馈仍失败：比R2-04多完成一个2.5度结点，第4结点67.83334s首次旋转越界，末5.384mm/0.567768rad。第三结点三指均有触、法向误差约0.1mm，随后仍快速转动；修正最大约0.052rad，没有触及0.08rad上限，不能据此继续提高增益。暂停延长这两种末段控制。先对55度假想滚动接触终点做独立A，检验新操作终点是否值得继续追求。该候选整根拇指能在几何上接近滑块，但功能姿态分支仍不可达；A将只在首次物理步前预置，随后实际停稳、使用实际状态/历史接冻结teacher，绝不注入B。初版A初始化因中指近节与刀具相交0.595mm被拒绝，正在仅调整首次加载的张开状态清除相交，闭合目标及物性保持。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T20:30:38.296225+00:00

R2-04失败在第二段第2个2.5度结点（累计名义约20度）：66.76667s首次世界旋转越界，末3.363mm/0.264985rad；中指无名指持续接触，食指第一段20%、第二段46.7%，拇指间隙>=4.55mm，未掉落、未进策略。停止继续延长这个开环方案。R2-05保留R2-04同一前缀和轨迹，仅在第二段加入R2-03相同参数的食指法向反馈。离线法向偏差约0.9mm，对应+0.045/-0.039rad修正在现有0.08rad界内，首命令差0，54个残差包络样本没有新指间碰撞对。备用反馈前缀第二段的初次几何因命令偏置超过原上限0.000924rad拒绝，已把名义求解限位与保留偏置后的电机限位取交集后通过；这是规划约束修复，未改硬件限位，尚未做该备用方案物理。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T20:22:53.039025+00:00

R2-03反馈对照通过原门禁：15度全运动食指持续接触，末1秒食指29/30帧、中指/无名指30/30，世界3.208mm/0.185534rad，拇指间隙>=4.676mm。与R2-01前1770帧q/臂/物体/腕/滑块/电机目标逐项完全一致；只新增食指法向反馈，峰值修正0.00862/0.06543rad，末法向误差-0.01178mm。不能称100%接触或长路径已成功。后续若分段使用反馈，新增明确停止边界：冻结最后实际电机目标作下一段初始参考，禁止把旧残差重复叠加；评分世界目标不变。R2-04累计名义30度在途，保留先重建后转腕路线；备用几何比较反馈路线下一15度。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T20:17:51.134034+00:00

R2-04从R2-02已验证前缀继续下一15度相对转腕，目标累计名义30度；不是注入末态。支撑点取真实重建接触帧，拇指已经离触，只做小幅避让。新段采样整拇指间隙>=4.519mm、无新增/增加自相交、无臂掌碰桌、支撑材料点误差<=0.465mm、手指速度峰值0.429rad/s；世界评分参考仍为原组合倾斜终点，已有0.1886rad误差不清零。R2-03反馈对照仍在运行；只启动这两项有信息区别的试验，原训练88339保持。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T20:15:18.823305+00:00

R2-02通过：15度转腕后用食指远端重新建立第三接触，末1秒三指100%接触、全拇指30帧无触、间隙4.552mm，固定原世界目标3.312mm/0.188584rad。仍未到滑块、未进策略。R2-03在原R2-01路径上仅加入食指法向位置积分修正（3/s、±0.08rad、0.2rad/s），运动前一次固定世界材料点和法向，首帧差0且离线符号/限速检查通过；所有物性与门禁不变。它与先失联再重建的R2-02是有区别的控制对照。长路径几何允许原指腹内滚动后从35度扩到55度，57.5度仍失败，只有几何证据。正在从R2-02真实重建接触末态规划下一短段，同时继续检查R2-03。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T20:06:34.496016+00:00

R2-01三指转腕目标失败：61.8000s食指首次失去有载接触，末1秒食指0%、中指/无名指100%；固定世界2.961mm/0.183261rad、拇指全无触且间隙4.938mm，未掉落、未进入策略。下一试验明确把这个已测1秒阶段标为两指保持，再仅动食指远端3/4重建第三支撑；不是把原失败改成功。按实际末态求解目标q3/q4=0.37775/1.46299，名义可达点x=-8.023,z59.234mm（原z35偏好未达到），根部和其他电机目标不变，最终仍要求三指1秒接触、原固定世界阈值和拇指间隙。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T19:57:43.274802+00:00

R2-01已从桌面启动15度三指支撑转腕。20度提案在17.5度拇指间隙低于4.1mm被几何拒绝；15度初版增加食中指根部交集，面轴约束仍不足，加入精确凸包交集约束后采样无新增/增加交集、拇指最小4.203mm、支撑材料点误差0.380mm，指令峰值0.529rad/s，臂速度上限占9.57%，无臂掌碰桌。所有拒绝几何保留且不计物理次数；新执行仍用固定原世界参考，并每段检查整拇指间隙。真实三接触静力LP在mu1/2/3有解、mu0.5无解，模型力非实测。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T19:50:55.810051+00:00

第一轮16次结束：R1-16三指支撑1秒通过，食指/中指/无名指100%接触、全拇指30帧无触，最小间隙4.562mm，同一原计划世界目标最大3.088mm/0.130637rad。与R1-15相比仅按真实校正末态重算远端食指目标，形成了缺失接触；与R1-14相比不能孤立归因，因为同时有腕部校正。最远为G1加稳定第三支撑，G2/teacher/student未就绪。第二轮优先实测三指支撑下相对转腕，若几何或执行受限，再比较已授权候选1支撑迁移；不增加获取候选，不启动未过门槛学习。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T19:50:02.827650+00:00

续接已实查R1-16子进程1502602及启动时间有效，旧训练88339仍在运行，GPU约91%。远端最新dffb0c2与本地提交一致；新增转腕插值预检工具正在用旧路径核对。第一轮16次已启动，等待最后实际接触保持结果后复核轮次。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T19:44:23.366913+00:00

R1-15一次固定目标校正通过：旋转误差0.2296降到0.11756rad，最大平移3.232mm，拇指全程无触；但校正中手物关系也改变，原样食指动作不再形成接触，故第三支撑仍失败。已从该试验校正后的真实停稳帧重新求解同一远端两关节策略，目标仍是刀底、没有改物性或预载规则；新目标q3/q4=0.68310/1.38544。R1-16保留原连续前缀和一次校正，仅使用匹配实际末态的食指计划。此为第一轮最后一次物理预算，结束后更新轮次决策，不重复无触计划。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T19:37:11.135642+00:00

R1-14远端两关节路径真正建立食指接触（末22帧，三指支撑），但53.7667s固定参考旋转首次超标，末1.925mm/0.254017rad，拇指全程无触间隙>5.19mm，未保持1秒，不能算成功。该路径确实避开原根部跟随偏差，却消耗了G1后约0.23rad的剩余裕量。R1-15仅新增一次腕部校正：在G1之后将刀身转回同一原计划世界朝向，用机器人电机2秒校正+保持，手指命令固定；实际修正界限0.25rad，原稳定阈值10mm/0.25rad不变，参考不刷新。之后原样执行R1-14远端两关节动作，检验初始偏差与接触建立能否分开解决。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T19:30:45.725765+00:00

R1-12末保持稳定但没有建立食指接触：3.334mm/0.21087rad、拇指无触间隙5.083mm，中指无名指保持；食指根部两关节实测偏离命令0.076/0.105rad，末端关节跟随约1e-6rad，不能将指令触底当实际支撑。R1-14有明确区别的对照仅动食指远端3/4关节，根部1/2与其他电机命令固定，几何目标在底面x=-7.24mm/z42.75mm，检测是否绕开根部接触耦合。R1-13第二获取候选成功完成取刀/翻掌/2秒保持，实际thumb+middle+ring承载；操作功能角差52.82度但中心偏差46.49mm，不能只凭角度声称更接近可操作。下一步同步审计该候选真实接触与拇指可达性。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T19:27:04.284850+00:00

候选2复核修正：之前把闭合电机目标的约0.5mm根部凸包相交直接当不可执行姿态，证据不足；闭合命令不会作为物理状态载入。已证实修正后的真正初始化张手姿态避桌3.132mm、食中指无相交，完整G2接近/抬起/翻掌运动学通过。仅初始选-.7腕分支，不把不可实现的固定腕末关节值强加于接近全过程；不改G2限位。R1-13启动第二且最后一个新获取候选的实际闭合/抬起/翻掌/2秒保持，原物性、有限驱动、自碰撞均保留，按真实接触与实测关节判断。R1-12第三支撑在途，两项物理可并行，旧训练保持。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T19:21:57.805282+00:00

首次90分钟方向复核：G1已通过；R1-11前17.5度真实支撑转腕均守住固定阈值，20度在55.6000s首次超0.25rad（末0.27606rad/2.238mm），仍中指无名指持刀、拇指间隙6.526mm，无掉落，不是teacher失败。新增旋转轴与两实际支撑点连线末段余弦0.88，支持欠约束滚转解释，但不排除接触滚动/电机偏差。停止直接扩大同一两指转腕；优先加原本无触食指第三底部支撑。新食指路径先在>4.236mm刀具间隙下移到z35mm底面，再建立接触并保持1秒。60度终点拇指几何可达，G2臂独立路径也可达；手指两支持路径在35度几何不满足，仍需支撑迁移。局部学习环境门槛尚未满足，不启动训练。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T19:16:06.339880+00:00

任意指腹几何正对照通过；原末态及6mm平移/25度相对转腕均未找到无碰滑块触点。预声明的第三个终点筛查60度相对转腕得到一条几何可行拇指分支：顶面点误差<0.1um、全根刀具间隙约0.059mm（接触终点，非离触门禁）、手指间间隙15.5mm。仅证明局部终点几何，不证明60度支撑、滑块全程或teacher能力。R1-11正在从桌面运行前25度支撑协调；后续依其实际末态规划，不能注入假想状态。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T19:14:34.434340+00:00

G2几何：固定指腹及任意指腹两分支均未找到直接滑块无碰接触；腕平移6mm也未改善。现已求得实际中指/无名指材料点保持、食指避让补偿、拇指电机固定的25度腕部相对刀身转动路径；这不是手刀整体旋转。每2.5度一段，手指指令峰值0.355rad/s，G2可达无桌碰；原初态食中指根部凸包交集内切半径0.157mm随路径减小至零，无新增相交。R1-11只检验这条连续支撑协调动作和末1秒拇指无触保持，刀身参考仍是原计划倾斜终点，明确当前约0.23rad误差裕量较小。任意指腹终点仍非操作已验证，尚不接策略。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T19:07:05.839865+00:00

G1结果已提交并推送0e220e8。正在做G2纯几何：任意指腹材料点筛查及第二获取候选食指/中指联合避碰。首次几何进程因BLAS过量线程及完整凸面轴计算过慢已仅停止本轮几何进程，改为单线程和保留全部顶点的32面轴保守预筛，终点仍用完整几何复核；无新增物理计数、未动旧训练。静力模型真实离触末态在mu2/3可行，mu0.5/1不可行，非实测接触力。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T19:02:09.840853+00:00

R1-10通过G1：一次小角度机器人校正回原计划终点后，拇指12mm退出及整根无触1秒通过；间隙最小5.252mm，固定计划世界漂移1.871mm/0.22955rad，中指无名指全时承载，小指离触。原物性及10mm/0.25rad不变。此对照支持初始跟踪偏差影响裕量，但末握持仍有约0.22rad手内转动，不能归因为唯一原因。继续G2，尚未进入teacher/student。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:55:43.569464+00:00

R1-09失败但未掉刀：拇指无触12帧、末间隙5.459mm，刀平移1.651mm，固定计划参考旋转0.25559rad超0.25；第一次越界48.7000s。小指在拇指完全离触前丢失，最终中指+无名指接触，末角速度已降至0.03rad/s，仍无1秒保持证据。R1-10单因素对照：在同一退出路径前，用一次真值测量做约2.4度电机姿态校正，目标仍是原来预声明的倾斜终点，绝不刷新参考；校正1秒+保持1秒后再退出拇指，阈值不变。检验先前0.0426rad跟踪偏差是否影响接管裕量，不能预认定唯一原因。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:47:05.495195+00:00

R1-08预声明30度组合倾斜及1秒保持通过：全轨迹位置误差6.709mm/旋转0.04281rad，末保持1.363mm/0.04274rad；原始世界转角0.5327rad是声明的主动运动，不作为偷偷放宽阈值。实际倾斜末态去拇指LP在mu2/3有解。R1-09启动：复用同一连续前缀，仅新增拇指实际材料点退出12mm并保持1秒，整根拇指要求无触且间隙>4.1mm；固定参考始终为倾斜前已声明的计划终点，不采用实测末态刷新。几何最终间隙11.54mm。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:40:41.780255+00:00

R1-07完成：新获取→食指左底接触1秒保持通过，0.607mm/0.004792rad；还不能释放拇指。R1-08启动有区别的重力方向对照：沿用R1-04真实左底中指前缀，手刀作为自由接触组合绕刀长轴转-30度，仅驱动G2电机。全部目标刀身轨迹运动前由一次真值固定，刀中心目标不动、末态保持1秒，仍按相对目标10mm/0.25rad并保留原始世界旋转；原物性不改。静力模型旧支撑在该倾角mu2/3可行，未倾时不行，模型不是物理证明。纯IK首命令2.8e-6rad、速度0.226rad/s、臂掌避桌通过。先验证倾斜保持，不立即放拇指。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:33:54.897555+00:00

R1-06完成：保留左底中指支撑后，无名指真无触1秒通过5.186mm/0.12102rad；没有运行碰撞的无名指底部终点。旧小指底部目标又与原无名指几何相交，因此旧路线不能直接再添加该目标。新候选1食指底部试验在途；下一优先筛中指在新腕关系下转到底部中心，利用已验证取刀时更充足的中指屈曲余量。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:32:09.314454+00:00

R1-07启动：复用新候选1真实取刀翻掌前缀，仅移动原本无触的食指到刀底左侧x=-4mm/z35mm。先下方避让再建立接触，计划全指刀具间隙最小4.081mm、目标前避让5.766mm；7点各指凸包预检最小间隙1.036mm，无几何重叠。保持阈值仍10mm/0.25rad，末段1秒真实接触。R1-06目前已到无名指无触保持，结果待结束审计。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:30:55.627010+00:00

R1-05新获取候选1已完成平放取刀/翻掌/2秒保持，漂移0.454mm/0.003021rad；实际为拇指中指无名指三点接触，食指和小指自由，非四指都接触。当前相对功能姿态81.88度/21.716mm，角度改善但中心偏差更大，操作能力未验证。旧路线无名指底部目标与拇指凸包相交已用LP确证，禁止执行该目标；R1-06只运行无名指卸载保持。正筛查新获取空闲食指/小指的底部支撑。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:27:07.526168+00:00

R1-06启动：R1-04左底中指支撑后仅无名指退出4mm并保持1秒，检查剩余支撑并获取真实卸载末态用于规划。完整无名指深避让目标在joint2/3限位，浅路径虽端点误差0.889mm但关节直线扫掠不满足1mm几何间隙，均已拒绝物理。下一步用实际无触末态做碰撞感知关节路径，不能只重复端点插值。R1-05新四指获取正在抬刀，尚未验证翻掌。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:24:24.419005+00:00

R1-04通过真正的中指避让迁移：先无触移位，再在左底面x=-3.459mm/z=14.167mm建立接触，接触为中指link4而非指腹；末保持4.339mm/0.13029rad。去拇指LP仍不成立，计划再补底部支撑。R1-05启动新获取候选1：四指侧夹、小指避让，名义相对角95.735→78.606度，掌朝向符合任务；普通端点IK有分支跳变，独立启用连续笛卡尔接近/抬起，纯运动学速度0.515rad/s以下、首指令<9e-6rad、臂掌无桌碰。G2伺服/物性不变，明确不同获取控制条件，不作单因素因果结论。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:16:13.488819+00:00

R1-04启动：中指先前移到刀身z=14mm并向下退出，随后在>5.6mm几何间隙下横移到x=-4mm，再建立底部支撑；全指横移扫掠满足4.1mm间隙，端点误差<1um。z=1mm的原下移目标限位不可达；新纵向位置是有界替代，不改物性。仍只动中指，其他电机固定，先保持不放拇指。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:14:51.119038+00:00

R1-02a完整通过中指两段移动及保持，但实际中指接触仍x=+5.675mm，未形成居中支撑；电机目标与实测有0.067rad差距。R1-03扩大退出路径后拇指真正离触，首次离触34.633335s也正是首次旋转失稳，随后刀掉出；只维持12帧无触，G1失败。证据支持原支撑缺少去拇指承载，而非拇指始终无法运动。中指深间隙路线上关节3限位，预筛失败未启动；现在筛查其他IK分支和已无接触食指的左侧底部支撑。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:12:21.620712+00:00

GitHub正常Git推送已恢复：普通工作树push的子进程读.git/config失败；使用本地独立bare发布仓库正常push成功，未改权限、安全、审批或凭据。远端新分支已建立a3afde1。R1-02中指第一次内移运动通过3.016mm/0.07638rad，仍等待完整保持及第二段。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:08:40.638079+00:00

R1-03启动：保留D04原支撑，同材料点退出方向，仅将拇指退出距离4mm改12mm。固定物体几何扫掠间隙单调增加至11.48mm，实际要求整个拇指零接触且间隙>4.1mm保持1秒；与R1-02支撑迁移独立。两项本轮仿真，旧训练保留。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:06:55.926006+00:00

R1-02a启动：D04真实前缀后仅中指在底面依次向x=0/-3mm滑动并各保持1秒，腕及其他指命令固定。全指扫掠几何为有意接触迁移，最大保守重叠指示1.27mm，不能解读为实测穿透或稳定证明。此前R1-02仅环境准备失败，无物理启动，已留记录。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T18:01:29.307878+00:00

R1-01失败于无名指从角部移到内部的运动阶段：39.6667s首次转角超0.25rad，最大0.25805rad/5.54mm；未到新支撑保持。现有路径只约束端点接触几何，1mm底面间隙小于4mm成对contact offset，需检查完整关节插值的扫掠体；下一对照只改无名指避让路径，保持接触终点与其余指命令不变。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T17:57:05.426736+00:00

R1-01启动：沿用D04中指迁移，改无名指底面x由+9mm到-3mm，z=-12mm；先建立支撑保持，不立即放拇指。真实D07无名指法向主要侧向，食指离触；简化静力LP移除拇指在mu0.5..3均无解（平均接触点模型，不是不可行证明）。新试验记录整个拇指几何间隙、实际接触及同步近景，主物性不变。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## Overnight G2 20260926 2026-09-25T17:54:13.448279+00:00

新过夜Goal启动：本地与GitHub均为7dea82e，干净工作树切独立分支；01:52:35至09:52:35北京时间，09:07:35开发截止。旧训练88339实查活跃，4090显存8.9/24.6GB，磁盘充足。先检查D07/D10/D11真实接触、整个拇指间隙与去拇指支撑可行性。新预算48次分3轮，当前0次；允许学习但门槛尚未满足。

续接：runs/g2-overnight-20260926/task-state.json；research/g2-overnight-20260926.md。独立分支feat/g2-wuji-overnight-20260926。开发截止北京时间09:07:35，总截止09:52:35。

## G2 分指换握 2026-09-25T17:02:15.151253+00:00

已发布并回下载核验：https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-finger-gait-20260926-v1，15个附件（10段完整无字视频、22.13MB增量证据及报告/校验）大小SHA和下载字节全部一致。代码/运行基准提交3e6486acef0a9a107595a490200cc40f7460c3a8，分支feat/g2-wuji-finger-gait-20260926；恢复D09精确源码3887项SHA通过，生成命令bash语法通过，未新增物理。报告research/g2-finger-gait-results-20260926.md。取刀/翻掌/双指底部支撑成立；拇指释放和整段teacher失败，student未运行。停止扩展并保留11次启动全部证据；下一优先检查去除拇指后的实际接触支撑可行性，再定义单次支撑预载对照。无本轮在途进程，旧训练88339实查仍活跃。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动11/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:57:12.248121+00:00

本轮物理已结束：11次启动、10次物理、9条连续B前690帧均与V2逐元素一致；全部11份源码pin共3878至3887项逐文件校验通过。最远D07取刀/翻掌/中指无名指底部换位保持；D09 teacher0.633s失稳、1.133s全失联、1.6s落桌，600帧离线接口回放误差0。D10/D11不同支撑未完成拇指离触，按停止规则收敛。先读research/g2-finger-gait-results-20260926.md；完整命令在research/g2-finger-gait-20260926.md。正在发布独立分支feat/g2-wuji-finger-gait-20260926及Release g2-wuji-finger-gait-20260926-v1；旧训练88339保留，C/新位置验证未运行。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动11/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:54:14.300531+00:00

D11 ended: middle+ring bottom support retained through prefix, but thumb unload first violates0.25rad at44.966669s, max0.27502rad/5.4165mm; abort before unloaded hold, no policy. D10 and D11 are two physically distinct support arrangements that fail the same minimal thumb-release objective; stop expansion per user rule, not budget exhaustion. Total11 launches=10 physical+1 preflight. Teacher D09 failed, C and new placements not run. Preserve all failures. Next priority is a bounded support-force feasibility/preload discriminator before another release attempt, not RL/retraining.

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动11/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:48:47.497721+00:00

D09 completed continuous teacher trial: pickup/flip/middle migration/hold pass, teacher operates600frames but drops knife; C gated, not launched. D10 actual-contact-anchor unload still retains thumb contact100%, pinky absent; corrected anchor alone did not solve release, stable but requested action failed. D11 tests physically different support (middle+ring both bottom), same4mm material-point thumb unload and1s full absence gate. If the same minimal action fails without new discriminating evidence, stop expansion rather than consume18 by tuning.

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动11/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:43:15.970220+00:00

D07 ring-bottom complete and stable: final hold5.378mm/0.1184rad, actual ring/middle/thumb/pinky contacts; index intermittently absent. D08 retained knife but FAILED requested thumb release: thumb contact100%, pinky0%; do not call unload successful. Actual thumb pad contact y=-1.15mm differed from mesh extreme y=-4.32mm. D10 isolates planning anchor: same D04 support, same4mm/1s, actual material contact point; new full-second no-contact gate. D09 tests frozen teacher from independently validated D04 held endpoint without arbitrary cache regrasp. 10/18 launches.

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动10/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:35:39.634903+00:00

D08 starting independent support contrast from verified D04: only thumb unload4mm and hold1s, middle already on bottom, ring/pinky original side support. Determines whether ring migration is actually needed to free thumb. Two local physics jobs within available VRAM; old training preserved.

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动8/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:35:10.845041+00:00

D07 starting: same successful D06 prefix, move ring via outside corner to reachable bottom z=-12mm. Twenty-point geometric screen found original z=-22.3mm at joint limit, z=-12mm feasible with residual<0.1um. Only ring motor changes; fixed wrist/other digits and original physics. Geometry does not prove stability.

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动7/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:34:11.066319+00:00

D06 finished: middle-bottom then ring unload held 1s, max fixed-world 5.382mm/0.12752rad; ring contact zero, thumb/middle/pinky remain. Budget 6/18 launches (5 physical). Original training88339 verified active; no gait processes remain. Next geometric ring-bottom reachable-point screen; preserve all pins.

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动6/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:32:03.566509+00:00

D05第5度失败中止：固定世界平移4.276mm、旋转0.30298rad，前4度未超门禁；不扩大腕转角。D06仅卸载无名指在途；下一优先单指迁移，不加反馈增益。D05接触字段已核对camelCase localPos0/1并采集。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动6/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:30:55.033265+00:00

D05正在逐度接触保持腕运动；第1度仍通过固定阈值。无名指底部迁移几何残差2.27mm，未做物理；D06只做中指已建立支撑后的无名指卸载+1秒保持，用于验证新的四指支撑组合，尚未迁移或转腕。18上限已由launcher按保守启动数强制执行。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动6/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:26:45.666437+00:00

D04终态通过。5度接触保持的固定腕平移插值在4度时中指不可达(1.57mm)，几何排除；允许腕部有界<=10mm平移后5度各指固定接触残差<0.00003mm，D05启动物理。此处只改规划腕路径，不改物性/动力学。D04日志未提供local_pos字段，接触位置仍是网格估计；新代码记录实际dtype并兼容camelCase，不能误报为已有实测接触点。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动5/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:24:47.704231+00:00

D04单中指迁移刀背边缘并保持1秒通过，最大固定世界漂移2.962mm/.07431rad。其余指电机目标不变；真实接触数据local_pos0/1开始记录。准备5度接触保持腕运动，逐度补偿指基座运动，接触目标不迁移。D03 A已通过，暂不增加其他目标A。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动4/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:22:17.196221+00:00

D03独立A当前腕姿20秒通过2mm/两轮/稳定：四端点0.563/0/0.252/0mm，世界7.122mm/.13993rad。不需要默认搬运；只证明终点手物关系有效。当前原侧夹固定腕刀关系下拇指到滑块多初值IK仍残差32.07mm，新近端点不可行。D04中指底部迁移在途。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动4/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:21:00.714980+00:00

D02中指卸载4mm并保持1秒通过：世界1.582mm/.02124rad；中指保持期接触0，其他四指全程接触且电机目标未变。D04开始单中指绕角建立底部支撑，原前缀与卸载复用。D01仅IK预检失败未simulate；同腕实际q用作求解种子的D03 A已进入物理，不更改限位。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动4/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## G2 分指换握 2026-09-25T16:18:06.764223+00:00

核对本机/远端277efe4一致，独立分支已建立。相对旋转103.6009度核算成立但非因果；保留抓姿0/1旧操作证据。D01 A当前腕姿、D02中指卸载各独立源码已启动，分别PID928290/933348。原训练88339实查活跃。

本轮分支feat/g2-wuji-finger-gait-20260926；实验runs/g2-finger-gait-20260926；开发启动2/18（含独立A）。先读research/g2-finger-gait-20260926.md及实验journal.jsonl。旧任务不重启、不覆盖。

## 2026-09-25T15:21:44.180461+00:00 取刀翻掌证据已发布核验

https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-sliderdown-air-flip-20260925-v1：9个附件大小/SHA全部验证，4项源码与轨迹（含两次失败）、四段无字视频、完整命令/报告；增量归档4.98MB，16项关键归档内容与本机源文件一致。源码分支feat/g2-wuji-air-flip-20260925已同步，Git HTTPS helper反复无法读取.git/config，改用GitHub Git对象API，校验树完全相同并已对齐本地分支。下一会话先读research/g2-air-flip-results-20260925.md；取刀翻掌通过、手内调整失败、无新策略操作这三点不变。没有在途本轮任务；保留原训练88339。

## 2026-09-25T15:18:20.908356+00:00 修正路线当前收尾

先读research/g2-air-flip-results-20260925.md。用户滑块朝下→取刀→小臂手整体180°翻掌已验证V2；后续V4开环和V5腕真值跟随均在手内调整失败，无新teacher/student操作。V5第704帧因52.1mm刀身偏移中止；4个物理进程已结束。下一项仅建议固定翻掌前缀、分指迁移的有界方案，未执行；无新训练，原88339保留。旧端立不再符合用户现实路线。即将新增Release只备份本轮4项和诊断；旧v6/v7不覆盖。

## 2026-09-25T15:15:42.797914+00:00 空中换握第一物理对照失败

V4前690帧与滑块朝下V2取刀/翻掌逐元素一致，后续12秒换握期间渐进转偏：第8秒0.329rad，第10秒0.663rad，第11.96秒1.317rad/28.5mm，滑块被动打开；在转运初段落桌，operation_steps=0。不要归因唯一为末段减压：减压之前已经转偏。完整42秒失败保留。

V5仅改 --seat-feedback object-truth，手指/物性/源码pin与V4相同（清单SHA5d1c7232…），使用既有5mm/0.05rad限速IK及50mm/0.8rad刀身范围；仍是理想定位对照。PID556357，结果待收。代码已推GitHub d4b68d8；origin是本机备份仓库，外部推送需从/home/agiuser/artgym-full-backup-20260925-v1/code-branch完成，主工作树HTTPS helper读取.git/config报权限错误，已用备份中转推送成功。

## 2026-09-25T15:08:45.606731+00:00 滑块朝下取刀翻掌通过；手内调整在途

B-sliderdown-pronate180-h30-v2完成25秒，750帧，无操作：滑块面朝上分量-0.9993→+0.9850，掌心-0.8043→+0.8044，实际翻179.821°；翻转期间刀手相对最大平移3.941mm、转角0.1556rad，无失联或落桌。完整末秒保持通过。手/刀物性同v1字节一致，臂关节位置与指令/实测速度无超限。预览http://127.0.0.1:8767/g2-sliderdown-pickup-flip180-v2.mp4。

从v2实际flip末态推导手内规划，不用它重设状态。单求解路径v3接触误差15.47mm被几何筛除，未做物理。v4加入功能角度种子比较，接触误差0.149mm、臂位置残差0.60微米；实际12秒换握正在B-sliderdown-airseat-teacher-v4 PID530855中验证。任何成功需读report/trace，不把几何路径当物理。原88339保留、无新训练。

## 2026-09-25T15:04:52.018916+00:00 用户补充初始滑块面朝下

当前正确路线：初始滑块朝下、掌心朝下侧夹→小臂与手整体翻180°→滑块和掌心朝上→手内调整→冻结伸缩。上一个v1滑块初始朝上仅为翻掌控制对照：750帧/25秒，179.818°，相对位移0.657mm，未掉刀；不代表修正路线完成。新v2从滑块朝下正常摆放开始，考虑3mm突出滑块，初始刀心0.7571m后自由静置2秒，再一次仿真定位规划抓取。没有改变刀/桌物性、没有夹具或端立。B-sliderdown-pronate180-h30-v2 PID508742启动，结果待核。

## 空中翻掌新路线 2026-09-25T14:59:32.827724+00:00

用户否定端立换握的现实适用性。当前分支 feat/g2-wuji-air-flip-20260925，运行目录 runs/g2-air-flip-v1；先读 research/g2-air-flip-20260925.md。改为掌心朝下取刀→空中约180°翻掌→手内调整→冻结策略。旧v6/v7保留，不再代表新路线成功。先验证夹持翻掌，无新训练；原88339保留。
> 当前活动目标已转为 **G2＋Wuji 桌面取刀→冻结策略**，请先读 [G2_TABLETOP_HANDOFF.md](G2_TABLETOP_HANDOFF.md)。本文件的 complete 仅指9月24日预置持刀旧目标；新目标仍 active，B/C尚未接通。旧4090训练保留。本独立工作树维护新记录，不覆盖原仓库的旧成功版本。

## 新阶段：G2桌面取刀→伸缩（2026-09-25）

2026-09-25 22:13 CST：本轮固定仿真基线+20次验证及增量发布已交付。独立工程 `/data/research/artgym-g2-tabletop-20260925`，分支 `feat/g2-wuji-tabletop-20260925`；先读该工程 `G2_TABLETOP_HANDOFF.md` 和 `research/g2-tabletop-final-report.md`。固定A63/B65/C66两轮10mm/稳定通过，B/C未全过2mm；C仍是仿真定位/理想初始化。20次小变化全部结束，B/C各初抬10/10、到接管0/10、整段0/10，条件操作未评估。小变化泛化失败，真机未验证；不能用固定成功宣称这些已解决。

成功视频在 https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-tabletop-fixed-abc-20260925-v6 ，最终验证/报告/代表失败在 https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-tabletop-validation-20260925-v7 ，全部附件及20次归档内容已核验。旧driver已终态，不重启或替换失败。无新训练，原训练88339仍运行。下一轮只建议获取转腕时长5/10秒的6次有界对照，尚未执行；继续时新建记录并保留本轮冻结成果。


## 全量备份本机部分完成（2026-09-25T04:44:30.604777+00:00）

本机3目录192177文件/208190472088字节已完整捕获、全量恢复核验；225分卷及元数据已上传并逐项校验GitHub SHA256，Release https://github.com/Jr-kelly/artgym/releases/tag/wuji-full-backup-20260925-v1 。详细完成记录 `/home/agiuser/artgym-full-backup-20260925-v1/FINAL.json` 与 `runs/wuji-goal/diagnostics/full-backup-20260925-v1-final.json`。远端SSH全部拒绝连接，远端独有文件待补，不能称所有机器全量完成；用户新入口到达后先拉取远端差异继续备份。后续新增CP/日志亦需增量。备份README内含下载、恢复、路径迁移说明。


## 全量备份执行中（2026-09-25）

用户明确要求全量备份到GitHub。备份工作根 `/home/agiuser/artgym-full-backup-20260925-v1`，spec.json 固定三个本机目录：原仓库、实验副本、早期demo工作树，约195GiB/19万文件，包含隐藏文件、.git、所有原始CP/日志/轨迹/失败记录/缓存与项目tmp。内容按64MiB块SHA256去重，封装标准tar+zstd分卷；manifest恢复全部路径。原4090 PID88339仍在训练，保留进程，备份逐文件捕获+第二遍变化核对，活跃日志记录为时间前缀，非原子整盘快照。

远端 .106/.93:30147、.73:30296、.59:31973 本轮全部Connection refused；已向用户请求恢复入口或新SSH地址。远端独有文件待补，不能把本地完成称全部机器完成。GitHub新Release tag拟 `wuji-full-backup-20260925-v1`，先完成可恢复验证再发布；工具在工作根tools/，进度status.json。查实际进度后继续，勿覆盖已封装分卷或冻结源码。 已创建Release草稿396269037；代码分支backup/wuji-full-20260925已推送。进程记录分别在备份根snapshot-process.json、upload-process.json、finalization-process.json，实际PID需重查；finalize_local.py会全目录恢复、逐文件SHA校验、上传元数据并发布本地部分。最终以FINAL.json为准，远端未连通前all_hosts_complete仍false。


## GitHub发布覆盖核验（2026-09-25）

本轮回答“是否所有进展和尝试都上传”，做只读GitHub核验：3个Release分页共1330资产（3/1000/327）；核心teacher+student17/17文件SHA256再次通过。66个本地发布目录中65个顶层文件全部按名/大小匹配，另一个有plot-provenance.json无同名独立资产，未据此宣称内容漏传。GitHub仅main与9月20日早期demo分支，后续源码以Release压缩包发布。最新sim2real分析、接续/日志尚未上传，也没有全工作目录/全部中间CP备份证明。完整状态 `runs/wuji-goal/research/github-publication-status-20260925.md`；API及匹配证据 `diagnostics/github-publication-audit-20260925-v1/`。本轮没有发布或改训练，审计时间 2026-09-25T03:09:08.927142+00:00。用户后续路线应保留简化模型、优先真实标定+DR，精细CAD按实机证据决定。


## Sim2real 与实物建模咨询（2026-09-24）

已核对在线原文v1及当前发布权重配置，详见 `runs/wuji-goal/research/sim2real-assessment-20260924.md`；原文回执 `research/sim2real-paper-source-20260924.json`。当前成功策略固定质量/摩擦/阻尼、jointNoise=0，尚无Wuji实物标定；基本仿真Goal完成不代表sim2real完成。论文采用独立实物开环重放选择有效物性、参数随机化、student闭环蒸馏、真实物体简化孪生和top5筛抓姿。建议针对最终真实刀具优先建模接触形状与启动/滑动/卡位阻力，同时核验Wuji指腹与执行器响应，然后敏感性评估、按标定结果随机化续训和重新蒸馏。用户此轮是咨询；这些后续实验尚未启动，没有改冻结模型/Goal或发真机指令。本次报告与交接已保存两个本机入口；远端 .106/.93:30147、.73:30296 均连接失败，镜像待连通后补，证据 diagnostics/sim2real-assessment-mirror{,-fallback}-20260924.json。记录时间 2026-09-24T07:21:47.446207+00:00。


## 本地视频打开方式（2026-09-24）

用户反馈 Firefox 直接打开本机绝对路径显示找不到文件；已实查两个视频存在且可读，未判定浏览器失败根因。已启动仅绑定 127.0.0.1:8767 的本地 HTTP 服务，检查时间 2026-09-24T07:13:13.967146+00:00，PID 4098（接手需重新核验）。

- Teacher：`http://127.0.0.1:8767/teacher.mp4`
- Student：`http://127.0.0.1:8767/student.mp4`

上述 URL 均 HTTP 200、video/mp4，下载 SHA256 与发布视频源文件一致。服务目录 `runs/wuji-goal/local-video-preview-20260924`，仅有两个视频别名；证据 `runs/wuji-goal/diagnostics/local-video-preview-20260924.json`，日志同名前缀 `-server.log`。用户执行 `firefox http://127.0.0.1:8767/teacher.mp4` 或对应 student 地址即可。服务只在本机可用，机器重启后须按证据中的 command 重启。没有重新生成视频或改变训练/Goal 状态。


## 最新结论：基本 teacher + student Goal 完成（2026-09-23T22:54:18.620350+00:00）

按用户最新定义，从预置功能抓姿开始，Wuji在现实尺寸参数化刀具上完成滑块伸出/收回；teacher和原本体感觉latent student均已通过冻结后新300初态物理验证。10mm到位换向，两策略各298/300至少完成3轮；student20秒294/300自然存活。外部固定2/5秒指令下，student全部端点10mm末段保持293/297（/300）。60秒快速操作仍会后期掉刀，2mm精度/严格刀身稳定也未解决；桌面取刀、未见物体与真机留后，不重设为本Goal前置条件。

最终报告：`runs/wuji-goal/research/core-teacher-student-final-20260924.md`。原teacher CP25 SHA4d8af063…，原pure latent student最终1000 SHA022ad8c7…；本轮没有新训练或挑峰值，只补齐任务对应的独立验证。刀具为刀身+被动滑块2刚体，147×19×11mm/35g，没有切割接触模型；Wuji控制/物性/奖励与论文有已记录差异，非全参数严格一致。

全部16运行条件已正常退出并重算，四段无字完整20秒视频（两策略×两视角）已检查；失败过程全部保留在证据包。17个资产已上传并验证GitHub SHA256 digest：https://github.com/Jr-kelly/artgym/releases/tag/wuji-experiments-20260923 。本机包 `runs/wuji-goal/release-core-teacher-student-20260924-v1`；发布清单 `diagnostics/release-core-teacher-student-20260924-verified.json`。主要视频前缀 `wuji-core-teacher-student-20260924`，文件名 `student-arrival-20s-three-grasps.mp4`、`teacher-arrival-20s-three-grasps.mp4`（发布文件含完整前缀）。

数值源pin V2，视频V4/V5源pin，V1–V3失败日志保留；不要修改这些固定目录。完整复现入口/运行命令在Release README。此次Wuji队列已经结束；原本机训练88339保留。四卡Sharpa6250参考训练已完成，八卡原上游参考及现有CP巡检依既定配置继续，不再新增teacher消融来延长本Goal。健康记录最新4h约四卡41.98%、八卡44.12%，完成任务后短窗已低告警，不用无效计算填充。

接续会话先读本段与最终报告，确认用户是否在提出下一项新工作；不要因旧文档中的硬件/宽泛化未完成就误把基本Goal重新判失败。下文为历史过程，涉及仍在训练/等待/工具blocked的表述以此段及goal-state最新工具记录为准。


## 06:45 CST：V4视频完成，补正面视角V5

V4两段无字20s/30fps视频都正常退出且已逐帧抽样检查，三抓姿均实际开合，后段失败保留。原视角主要看到刀身背面/侧面，滑块被遮挡，因此追加V5，仅给同一审计脚本增加相机参数，位置[0,.11,.72]、目标[0,-.11,.55]，不改动作/物理/资产/权重/初态。源pin `core-video-front-20260924-v5` 3686文件验证，八卡GPU1/4队列200297/200298。数值实验仍是V2。两种完整视角一起命名发布，不裁掉失败。

刀具URDF是刀身+被动滑块两刚体参数化模型，没有刀刃/切割接触模型；本任务验证滑块伸缩，与当前“先完成ArtGym式teacher+student、后续取刀”范围一致。模型的现实尺寸不等于物性已实物标定。


## 06:38 CST：全部六种正式数值条件已完成并从物理trace重算

|策略|时长|至少3轮（10mm到位换向）|全程自然存活|平均循环|
|---|---|---|---|---|
|teacher|20s|298/300|191/300|15.37|
|teacher|60s|298/300|143/300|37.20|
|student|20s|298/300|294/300|17.00|
|student|60s|298/300|240/300|42.95|

Student外部固定2秒/5秒指令各300新初态，10mm全部端点末0.3秒保持293/297；原2mm+严格刀身联合126/184；自然存活296/297。符合用户收敛后的基本开合任务，不等于2mm精度或60秒长期可靠。两权重和三个功能抓姿在新300上已验证，未进行新训练、筛行或更换峰值CP。新实验保留Wuji必要差异，不能称完全复现原论文所有参数。

还未完成的本次交付仅为：无字视频生成/检查、打包发布/哈希回读、最终交接和Goal完成标记。V1/V2视频初始化崩溃；V3已修好EGL但顶层assets符号链接导致仿真器相对URDF路径失败。V4把同一源码/资产目录实体化，所有3686hash不变，runner overlay SHA `98f9f5fe050e11742beab29acc9ab02c6a2f4ad71a336dad5a462bf879afa18f`。视频八卡GPU1/4队列197136/197137（新目录V4），前面失败全部保留。

采集：`python -m scripts.collect_wuji_core_evaluation`（数值V2+视频V4）；全14条件队列完成后 `python -m scripts.package_wuji_core_task`，输出 `runs/wuji-goal/release-core-teacher-student-20260924-v1`。检查视频后上传当前Release394720794/Jr-kelly/artgym，验证digest，再标记基本Goal完成。工具当前仍blocked，尚未调用complete。无需额外扩大teacher消融/硬件实验才能完成本次范围。


## 最高优先级：用户澄清 Goal（2026-09-24 06:16 CST）

仿照 ArtGym 的 teacher → student 流程，将 Sharpa 换成 Wuji；从预置功能抓姿开始，在现实尺寸美工刀上学习并闭环完成伸出、收回。完成 teacher 和 student 的仿真验证；桌面取刀、真机标定和广泛未见几何泛化为后续阶段。

详见 `runs/wuji-goal/research/goal-scope-teacher-student-20260924.md`。该范围覆盖下文所有旧“硬件/宽泛化为前提”的表述。已有 teacher 可用，接下来优先原本体感觉 student；保留旧严格指标，补测到位后换向的 10 mm 开合协议。已有 teacher 多 seed 有界收尾，不再扩充消融矩阵。Goal 工具 blocked 与授权实际执行分开记录。


更新时间：2026-09-23T19:45:39.814664+00:00。最新状态以如下03:45段及 research/progress-20260924T0345.md 为准；旧状态存 research/handoff-history-20260924T0345.md。


## 06:28 CST 审计与图形修复（V2）

V1到位换向正式20秒在最后一步断言失败：ArtManip._get_dones把回合超时也放入truncated_envs，原审计只排除了fall/invalid。V2记录timeout并在到位计数中排除，存活指标仍把正常跑满计作存活；没有改仿真、动作、权重或初态。增加真实回合边界语义测试，5测试全部通过。V1预检完成记录有效；正式失败不计成功，失败日志保留。

V1视频在创建图形时-11退出；V2采用已验证RGB运行方式，取消CUDA可见设备重映射、CUDA/Vulkan均指定同一物理GPU、设置NVIDIA ICD。新pin `core-teacher-student-evaluation-20260924-v2`，SHA `bdefce16af75fb0a7d25116b0b2e07f78b543b7bc2239980e0482820d341667c`，3686文件远端验证。队列193656/193657/193658/193659，对应八卡GPU1/3/4/5；无字视频193660/193661按租约等待。原固定时钟四卡任务独立完成，不重复运行。

新的固定2秒300初态结果：旧严格联合126/300；10mm所有五轮末段保持293/300，各组97/100/96；296/300自然存活。当前只引用已完整重算的结果，后续查看 `diagnostics/core-task-collected-20260924-v2/latest.json`。采集命令默认已改为V2；V1记录仍可通过 --version v1读取。

## 当前执行：Wuji teacher + student（2026-09-24 06:23 CST）

先读 `runs/wuji-goal/research/core-teacher-student-evaluation-20260924.md`。冻结原 teacher CP25 和原纯 latent student 最终1000；新300未筛初态已生成，20/60秒到位换向及原固定2/5秒评估已启动。八卡队列191112–191115、四卡327940；无字视频191730/191731按租约等待。Student20秒三个旧预检实际19/16/16循环，不能替代新300。采集命令：`/home/agiuser/miniconda3/envs/artgym/bin/python -m scripts.collect_wuji_core_evaluation`，结果 `diagnostics/core-task-collected-20260924-v1/latest.json`。

原 teacher 四新增seed8臂及176项物理/评分已全完成，seed203/204终审同步发布在途；不再扩大teacher消融。新 Goal 以本体感觉student基本开合为优先，旧广泛泛化/硬件门槛不再阻塞。

## 最新接续：2026-09-24 03:45 CST

先读 `research/progress-20260924T0345.md`。严格终止第一seed100和44评估齐：小300/300两时钟、宽279/283，第四0/32，未达广泛泛化。旧终止打包故障已补齐helper，新恢复2876724已在publish；第二reset seed、归一化配对已发布。

四个新增seed201/202/203/204（完整seed20261201–20261204）共8臂100轮配对开始。八卡训练series125766(GPU1,201→203)、125768(GPU3,202→204)；评估series125767(GPU4)、125769(GPU5)；scorers125770–125773。首两臂实际teacher126772/126763，门禁/预检通过。后续seed排队。四本机终审2873738–2873741。source pin `termination-multiseed-20260924-v1`，archive SHA df3d7872d962872a12375e9cc40c5ee90612a5f42fcd3de9bd503198d3b98981。元数据 `diagnostics/termination-multiseed-preparation-20260924-v1.json`，启动 `diagnostics/termination-multiseed-launch-20260924-v1/`。每组所有44旧开发条件，最终须另做新独立验证。

Sharpa四个CP3000/4000×100随机评估齐，共114800试验，矩阵重算通过。原/修复执行SR：53.22/55.88%，52.09/54.44%；GC未持续改善，不是严格公式复现。长训练约5950/6250(corrected)、4750/6250(upstream)。03:35滚动4h四卡45.46%、八卡33.59%，八卡短窗低告警；新任务03:44瞬时65.75%，不能当长期均值。原4090 PID88339保留且实查。

## 历史核验：2026-09-23 23:08 CST

第二seed两臂100和44评估全完成。2x最终CP100小扰动300/300、300/300；宽265/300、278/300；第四0/32。全部是已观察开发集，无CP同时过宽两时钟95%，未达总体目标。详见 `research/teacher-progress-20260923T2308.md` 与 `diagnostics/teacher-status-20260923T2308-summary.json`。

第二seed下载809497/评分809498已完成，终审1000149在publish阶段。归一化两臂100完成，八卡64822完成41/44物理、64823重评分40/44；最终adaptive100待齐。native终止100完成，strict门禁10000/预检3轮通过、正式CP25，四卡teacher294373；八卡75115完成19/44物理、75116重评分17/44。原训练88339本轮直接实查存活。4hGPU约59%/59%，五分钟巡检及文档镜像继续。下文更早的pending/CP10记录是历史状态。

## 先读与约束

1. 实验根 `/data/research/artgym-experiments-20260921`，非Git；原仓库 `/data/research/artgym` 保留。本文件在两根目录和共享远端有镜像。
2. 再读 `runs/wuji-goal/goal-state.json`、`runs/wuji-goal/health/LATEST.md`、`runs/wuji-goal/journal/events.jsonl`。下文短路径默认在 `runs/wuji-goal/`。
3. **不创建子代理。保留本机原训练88339。** 不改在途源码pin；失败/取消保留，新尝试用新目录。IsaacGym先于torch；GPU子进程用 `runtime_environment` 与本机 `/tmp` 独占GPU租约。
4. 用户授权持续研究、训练、修复及向 **Jr-kelly/artgym** 发布命名可视化；视频无文字。仅有用计算，平台GPU四小时均值门槛26%，目标>40%。不能将脚本/训练内/旧开发集/特权真值说成独立或硬件成功。
5. Goal工具仍外部blocked，无可调用resume接口，客户端命令 `/goal resume`。授权工作实际继续；未达目标不标complete。

## 机器与运行环境

**.106:30147和.93:30147是同一八H100机器两入口**，不是16卡。hostname `d-20260921021501-6zzgt`。四卡.73:30296 hostname `d-20260920124121-d9ns7`。两机共享GPFS文件、PID命名空间不同，远端无rg。

```bash
ssh -p 30147 -i /home/agiuser/.ssh/id_ed25519_h200 -o IdentitiesOnly=yes -o BatchMode=yes wangjiarui@10.14.0.106
ssh -p 30147 -i /home/agiuser/.ssh/id_ed25519_h200 -o IdentitiesOnly=yes -o BatchMode=yes wangjiarui@10.14.0.93
ssh -p 30296 -i /home/agiuser/.ssh/id_ed25519_h200 -o IdentitiesOnly=yes -o BatchMode=yes wangjiarui@10.14.0.73
```

远端根 `/home/wangjiarui/artgym-experiments-20260921`；Python `/home/wangjiarui/artgym-runtime/bin/python`。本机Python `/home/agiuser/miniconda3/envs/artgym/bin/python`。模块cwd/PYTHONPATH须指向pin及pin/rl_games，避免editable原仓库。CPU unittest用discover避免tests包冲突。

**新增已验证环境修复**：Python runtime的LD_LIBRARY_PATH会令系统SSH加载错误OpenSSL（built3.0、loaded3.6，退出255）。`scripts/host_tool_environment.py`只为SSH/rsync/curl/gh移除LD_LIBRARY_PATH/LD_PRELOAD并优先系统PATH，仍保留用户gh路径。Python/物理运行环境不变。2单测、污染环境下真实远端hostname和Release394720794读取通过。三个旧终审在0审计/0打包且无子进程时取消，训练/评估未中断；不要重启旧终审。证据 `diagnostics/host-tool-finalizers-{validation,launch}-20260923-v1`（launch为.json）。

## 当前任务

|主机|任务|PID|状态/入口（diagnostics下）|
|---|---|---:|---|
|本机|原训练|88339|保持，本轮已实查|
|本机|五分钟健康巡检|3132243|注册表goal_health_monitor.json|
|本机|五分钟文档镜像v2|760633|handoff-mirror-20260923-v2|
|本机|第二seed CP下载+物理评估|809497|reset-range-seed2-local-evaluations-20260923-v2|
|本机|第二seed五分钟独立评分|809498|reset-range-seed2-cp-audit-monitor-20260923-v3/LATEST.md|
|本机|第二seed完整终审v4|1000149|reset-seed2-finalization-20260923-v4，等44|
|八卡GPU0|归一化CP评估v3|64822|reset-normalizer-evaluations-eight-20260923-v3|
|八卡|归一化五分钟评分|64823|reset-normalizer-cp-audit-monitor-eight-20260923-v3/LATEST.md|
|本机|归一化完整终审v4|1000151|reset-normalizer-finalization-20260923-v4，远端读取恢复|
|四卡GPU1|新终止阈值配对|290813|termination-pair-20260923-v1，native实际门禁/预检通过，正式CP10，teacher292518|
|八卡GPU1|终止阈值CP评估|75115|termination-evaluations-eight-20260923-v1，已获得GPU1，基线/CP实际执行|
|八卡|终止阈值五分钟评分|75116|termination-cp-audit-monitor-eight-20260923-v1|
|本机|终止阈值完整终审v2|1000171|termination-finalization-20260923-v2，远端读取正常|

第二seed训练284122已两臂100/100正常完成；归一化训练286696已两臂100/100正常完成（14:23:10）。各配对32,768,000正式转移，两份完整训练审计已回传本机：`reset-seed2-training-completed-early-audit-20260923-v1.json`、`reset-normalizer-training-completed-early-audit-20260923-v1.json`（均在diagnostics）。终审将另做完整训练+评估+发布审计，输出名不同不冲突。

### 资源及参考实验

四卡Sharpa corrected：launcher106419、GPU0/3、最近CP5400/6250；CPscheduler287262、池[2,1]。八卡原Sharpa upstream：GPU6/7、最近CP4150+ /6250；第二seed upstream22713和corrected22714均500完成。helper44720于14:05:54完成，八卡CPscheduler已改为 **71673，池[0,2,1,3,4,5]**；新Wuji任务按租约等待，不取消既有worker。

14:24健康：四卡4h56.60%、5min64.45%；八卡见LATEST，均无告警。26%平台口径与本机采样区别保留。物理评估一项CP含多几何，持有租约直到完整worker结束，不能只看到新任务等待就认定GPU空闲。

## 三组续训定义与最新解释

共同原teacher SHA `4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac`。每臂从该权重及原输入统计开始、新Adam、LR1e-5、5120×32×100=16,384,000正式转移；另10000实际转移门禁+3轮491520转移PPO预检，正式重新从原权重开始。只采样三个原始训练抓姿在线扰动，绝不采样评估行。

1. **第二扰动seed20261128**：1x再2x。1x为位置分量±0.5mm/关节±.01rad/旋转向量分量±0.5度；2x翻倍。run `wuji_bridge3_reset{1,2}x_cp25_seed20261128_v1`。训练spec `reset-range-seed2-20260923-v2-spec.json`，sourceSHA `ff94128c8c14782b86c804c62dd169187ae57c2abdef4e5a2b02a67e14637088`。评估queue `reset-range-seed2-evaluation-20260923-local-v2-queue.json`：仅改未开始CP顺序，条件名仍-local-v1，4个原基线逐字节复用；旧错误等2x队列0物理取消，证据order-correction-v2。1x最终小283/290、宽237/257（/300，2s/5s）；2x待完整评分。不得只挑峰值。
2. **输入统计seed20261129**：两臂都2x，仅冻结/更新input normalizer；actor/critic/value统计训练。run `wuji_bridge3_reset2x_norm{frozen,adaptive}_seed20261129_v1`。spec `reset-normalizer-pair-20260923-v1-spec.json`，训练sourceSHA `ad03ffc10e35e0b1f9d91636b5c310982a7edbc447f678db03900612673d5c7a`。两臂100完成。frozen五个CP输入统计逐元素等于原值、count73728001；adaptive最终count93388801，权重/价值统计均更新且有限。证据 `diagnostics/normalizer-frozen-allcp-statistics-20260923-v1.json`。八卡GPU0/batch332/seed20261125重测全四基线：小294/298、宽261/267。frozenCP10宽270/281，CP25宽261/281，CP50宽254/274；冻结统计仍不能消除阶段性退化，完整配对待齐。评估sourceSHA `eed6f9f44a127d2ec19890bb24b942626b9f7a1aea544df5847458fb893fcf09`。
3. **新终止阈值seed20261130**：两臂2x、归一化正常更新，仅训练终止native(.05m/1.57rad)对strict(.01m/.25rad)。奖励/绝对位姿惩罚/动作/物理保持。run `wuji_bridge3_reset2x_done{native,strict}_seed20261130_v1`；spec `termination-pair-20260923-v1-spec.json`，suite `wuji_termination_pair_20260923_v1_suite.json`，sourceSHA `0ccd340eb4353011a4e9562bd8cf7aec87a0e4fc8da7486965de0236e4486400`。3673源文件本机/远端验证，真实Hydra合成仅两个终止阈值不同；本机配置v1导入阶段非零、原因未定、0物理，v2和远端v1成功，失败保留。native实际10000步门禁（125次动作映射、终止mask0不一致）和3轮PPO预检通过，正式CP10已出，strict臂仍按先后顺序等待。八卡GPU1评估所有模型仍用原生终止，然后同一严格规则离线评分，不能用改评估环境制造提升；重新测四基线，44条件统一GPU1。原>终止与验收<的等号差异已记录。

三组全部评估原baseline+两臂CP10/25/50/75/100，各小/宽开发扰动、2s/5s，共44。每条件600×332，前三组各100、第四32保留。任何本机/H100/4×83/不同seed协议不直接混用。固定最终CP和全曲线都保留。

### 新终审版本与源码

- 第二seed `reset-seed2-finalization-20260923-v4-spec.json`，sourceSHA `70c873461e1a00f457dfb43fc8f817054d68c7fcc2b91aa86b3e1be2a40e57ff`。
- 归一化 `reset-normalizer-finalization-20260923-v4-spec.json`，sourceSHA `101327978af15c0041ee53060136cc2678f0b4b17d732405eb7ac833f312955a`。
- 终止 `termination-finalization-20260923-v2-spec.json`，sourceSHA `3a81a80666167dc00c05a7026e51efea1bb42dc0763e9d7d910d60622ff8cb5d`。

终审等44齐，回传trace/CP/日志/门禁，核验哈希与预算，分析全曲线，打包并上传**新Release394720794**。实际H100评分器源码随包；不是旧local评分器。旧879492/879498/974473已在等待0审计/0打包且无子进程时取消，记录保留。新终审已真实读到远端monitoring且无OpenSSL错误。

## 已完成关键证据

### 第一扰动seed20261124：两臂100、44全量评估

|模型|小2s/5s|宽2s/5s|宽刀身稳定2s/5s|
|---|---|---|---|
|原teacher|298/299|252/263|258/264|
|1x最终100|282/282|242/252|259/274|
|2x最终100|294/298|262/279|274/284|

各/300，第四0/32。32,768,000训练+8,764,800评估转移全量审计。2x每个预定CP的宽快/慢均高于1x，但只有此单seed时不推泛化。无候选同时过95%两时钟门槛。`diagnostics/reset-range-cp-audit-monitor-20260923-v2/audit-44-20260923T131828Z.json`、`reset-range-control-analysis-final44-20260923-v2`。43/43附件在原Release全部digest核验，包括11权重/全部trace/日志/pin。

### 冻结归一化/持握机制：22阶段完成

同四卡H100GPU2/batch332/seed20261127，6门禁+16正式，3,198,000转移，全正常退出+逐条评分。No-op与native两时钟全部10个trace数组完全相等。原teacher261/267；CP100原生258/278、换原统计266/282；原权重换CP100统计229/258；CP50原生252/280、换原统计262/279。固定初始目标任务0/0，但刀身278/300稳定（.5s时280）。动态策略能救回部分固定持握失败，因此后者不是机械不可行证明。

原权重换CP100统计快损32（修复10、退化42），描述性配对区间-15.0至-6.33pp。CP50/100换原统计改善区间跨0；不能宣称统计是唯一原因或换回即解决。`research/reset-normalizer-mechanism-20260923.md`、`diagnostics/reset-mechanism-analysis-complete-20260923-v2`；原始trace在`reset-mechanism-gpu2-20260923-v3`已回传。**新Release11/11小型附件digest已验证**；附件不含raw trace本体，原权重/trace另有完整包。

### 终止目标离线诊断：44原轨迹、0新增物理

2x最终快速：原生存活292、严格刀身274、完整成功262/300。26次严格刀身失败中20次重获至少9帧稳定，实际界外时长中位.1s。故不能说多数长期掉落后赚奖励；有短暂越界后恢复，也有稳定刀身但端点不达标。评估关闭到位奖励，此处近目标时间不是实际训练回报。严格终止是否改善学习必须看新配对，也可能妨碍恢复探索。

`research/termination-objective-gap-20260923.md`、`diagnostics/termination-gap-analysis-20260923-v1`；分析pinSHA `4d699aa0863db870a11569945437ca76c856f35dea40bf7a95e18b1ea4f62cdd`。图已查看，`termination-gap-plot-20260923-v1/failure-categories.png`；新Release **5/5附件digest验证**，`release-termination-gap-20260923-v1-verified.json`。图与分析是原44诊断，不能当新终止训练结果。

## 已有独立RGB结果与边界

冻结混合RGB在冻结后生成的新小扰动300初态：287/300快、294/300慢，通过当时总体95%/每组90%工作门槛；只三个已训练抓姿的新扰动。证据 `rgb-independent-final-rescored-1802-v1.json`、`research/wuji-rgb-independent-result-20260923.md`。更宽300后来变为开发集，RGB237/255、oracle真实teacher258/266、因果真值253/263（这些为**旧4×83协议**）。第四抓姿始终0/32，不能称作广泛抓姿/未见几何/真机成功。

实际自主sensor旧开发332：288/295，CPU接口审计通过；CPU模型p50 4.69ms/p95 5.83/p99 6.35，不含相机/通信/电机，不是CPU物理闭环或硬件结果。RGB/runtime仍绑定原teacher，不能更换teacher并伪造元数据。混合RGB SHA `9221141fe68ec6c116d0b30fab1415794a0eefa48b4c0e8591ba7afe00669d28`；宽集SHA `ecb5989f1739a346f4fed5f174a98261737a069d94bff45a753538466168e025`。

现实刀147×19×11mm、35g、50mm行程/40mm目标。Wuji20DoF，支持指±.04rad、拇指±.025rad/步，阻尼.3未实物标定。统一严格20s、30Hz控制/120Hz物理，外部2s/5s指令，末9帧<2mm，刀身全程<10mm/.25rad且有效存活。

Sharpa论文22DoF、功能抓姿/人工放置、当前物体特权teacher、50帧TCN、10mm到位；不含自主取刀。当前upstream/corrected参考与明确paper公式失败分支有差异，不能统称完全对齐。文献与既有失败 `research/sharpa-success-and-wuji-student-gap-20260922.md`。SAPG聚合KL含跨探索组差异，不是同策略更新距离；旧零LR诊断同策略精确KL=0但聚合约.15-.31。现续训预检原聚合阈值不当作精确KL证据。

## 发布、备份和下一步

新Release：https://github.com/Jr-kelly/artgym/releases/tag/wuji-experiments-20260923 （ID394720794）。原：https://github.com/Jr-kelly/artgym/releases/tag/wuji-visualizations-20260921 （ID392488331），已经1000附件上限。原附件全保留，GitHub422证据`release-reset-mechanism-upload-diagnostic-20260923-v2/diagnostic.json`。新Release仍同基础commit313ba8ea，真实实验源码以附件pin为准。不要使用硬编码旧ID的上传器。

最近全局source snapshot224423 SHA `00832458e7bd71c73a43abf0ce605a4e7a2a9bc8b99fb82264483538179cdf53`；source-sync-files同步完成，本次archive与manifest远端回读SHA一致；前一批16个附属artifact的回读记录保留在222802验证文件。本次证据`source-history/source-snapshot-20260923T224423-remote-verified.json`。快照早于此即时文档属于正常版本差异。

镜像760633每5分钟读取稳定字节、同步并回读SHA，动态跟随registry.local_runs；远端拥有的状态不能加入local_runs。镜像spec`handoff-mirror-20260923-v2-spec.json`；sourceSHA `e70ae2181a04c11fe90114a3537122cdc848d9c3b99f817b6fd61d8bdf8a9067`。source同步不要覆盖监控配置和remote status，不展开pin/runs链接。

下一步按优先序：

1. 继续检查新终止native正式训练；它完成后strict臂须实际10000转移门禁/3轮PPO预检再正式。75115已在八卡GPU1按44队列评估。失败保留，不改在途pin。
2. 等第二seed和归一化全44评分，核查新终审1000149/1000151读取正常、按新Release发布；终止终审1000171同理。
3. 读全CP、身体/端点分解与配对差异；不从一个CP峰值宣布成功。归一化CP50已有退化，冻结统计单独不足。
4. 候选调参结束后冻结，重新生成**新独立行**验收；已观察宽集不能再称盲测。新teacher还要重新验证/训练RGB兼容。更广抓姿、未见几何和硬件未完成。

## 离线补充：初态与策略互补 2026-09-23T14:40:29.685251+00:00

`research/early-failure-policy-coverage-20260923.md`：16个机制条件全部重新核验，八种控制器共同前.5s失败的开发行仅0/4/87；四个学习权重的事后成功并集快289/慢293，同一权重两时钟成功覆盖288/300。是事后标签并集，**不是可部署策略或独立成功**；没有训练/选择新模型，没有删除失败初态。此结果只为后续策略保留/选择研究提供线索，先收齐现有配对。0新增物理。

## 最新训练/评分补记 2026-09-23T14:44:23.247659+00:00

native终止臂CP10 SHA`ded1cd09c1d0d8dc4464289538f7a0ca49fb4b060131d81eea4ac88273f8af84`；门禁实际10000判定，原生fall4个元素、严格身体越界143个元素、mask不一致0。3轮预检输入统计73728001→74317825、actor/critic/value更新且有限；聚合KL .03542/.01580/.02159，不当精确同策略KL。证据`diagnostics/termination-native-early-training-check-20260923-v1.json`。strict尚未开始，不宣称已通过。

归一化冻结组最终100已评：小278/289、宽243/261（/300）。相较同H100基线294/298、261/267退化，尤其宽B组57/73；全部五CP统计实际冻结，因此输入统计改变不是必要退化条件。adaptive完整结果待齐，不提前认定最终优劣。当前4hGPU四卡57.89%、八卡56.73%，无告警。106/93本轮重新对照hostname/boot/全部8个GPU UUID完全相同，证据`diagnostics/host-alias-reverified-20260923-v1.json`。

官方Goal恢复命令已于2026-09-23T14:46:20.357473+00:00重新读取确认：https://learn.chatgpt.com/docs/developer-commands?surface=cli ，`/goal resume`。工具仍返回blocked且此会话无resume工具，后台训练/巡检/评估正常进行；不虚报工具状态已恢复。


## 自动更新：第二训练seed完整审计 2026-09-23T15:29:04.530182+00:00

两臂训练、44条件评估和Release上传已审计。分析 `runs/wuji-goal/diagnostics/reset-range-seed2-control-analysis-final44-20260923-v1`；发布核验 `runs/wuji-goal/diagnostics/release-reset-range-seed2-complete-20260923-verified.json`。均为已观察开发集，下一步读取两臂完整对照并冻结候选后另做新独立验证。


## 自动更新：输入归一化配对完整审计 2026-09-23T15:46:48.453073+00:00

两臂训练、44条件评估和Release上传已审计。分析 `runs/wuji-goal/diagnostics/reset-normalizer-control-analysis-final44-20260923-v1`；发布核验 `runs/wuji-goal/diagnostics/release-reset-normalizer-pair-complete-20260923-verified.json`。均为已观察开发集，下一步读取两臂完整对照并冻结候选后另做新独立验证。


## 论文对齐复核 2026-09-24 00:16 CST

最新对照表 `research/paper-alignment-current-20260924.md`，source哈希 `diagnostics/paper-alignment-current-20260924-evidence.json`。当前成功teacher属于Wuji迁移，**未严格对齐**奖励/控制/物性随机化/数据规模/预算/评估。Sharpa公式分支仍数值失败，upstream/corrected不是公式相同。归一化与终止各44评估已完整；终止strict最终300/300小、279/283宽，第四0/32。终止打包v2缺package_wuji_dagger_final，失败保留、新pin修复。00:10八卡短期利用率低告警（5min21.76%，4h60%），需要补充有用计算。上文23:08 pending已过时。


00:18续接：补充四项有用的Sharpa匹配预算评估，upstream/corrected各CP3000/4000，五个未见几何全部有效抓姿各100次随机rollout。它只把该项重复数补齐，不能称完整论文公式复现或新的盲测。八卡GPU1/3/4/5，PID105768/105769/105770/105771；00:19已实查四个物理子进程105784/105781/105782/105783均在030运行，四卡GPU采样95%/97%/95%/96%。旧参考训练及CP监控保留。固定源码复用reset-normalizer-evaluations-eight-v3（archive SHA eed6f9f44a127d2ec19890bb24b942626b9f7a1aea544df5847458fb893fcf09），新增driver SHA ee4166ee86185c91ed58a5c9d42699776c4bdd3b32af99509ef6cdb51ad72f3c。配置、源checkpoint哈希、进程见 diagnostics/sharpa-matched100-20260924-v1/{spec,launch}.json。使用/tmp独占GPU租约，已加入五分钟健康注册；接下来收集四结果和逐项重算IC/GC/CSC，不把CPU包装故障误作训练失败。


终止配对发布修复完成 2026-09-23T20:05:22.109484+00:00：runs/wuji-goal/diagnostics/release-termination-pair-complete-20260924-v2-verified.json，全部附件digest通过，0新增物理。


## 自动更新：终止阈值seed20261202完整审计 2026-09-23T21:24:03.411190+00:00

两臂训练、44条件评估和Release上传已审计。分析 `runs/wuji-goal/diagnostics/termination-seed20261202-20260924-analysis-v1`；发布核验 `runs/wuji-goal/diagnostics/release-termination-seed20261202-20260924-verified.json`。均为已观察开发集，下一步读取两臂完整对照并冻结候选后另做新独立验证。


## 自动更新：终止阈值seed20261201完整审计 2026-09-23T21:29:03.789159+00:00

两臂训练、44条件评估和Release上传已审计。分析 `runs/wuji-goal/diagnostics/termination-seed20261201-20260924-analysis-v1`；发布核验 `runs/wuji-goal/diagnostics/release-termination-seed20261201-20260924-verified.json`。均为已观察开发集，下一步读取两臂完整对照并冻结候选后另做新独立验证。


## 当前工作与目标核对：2026-09-24 06:08 CST

本轮远端实查：新增四seed共8臂100epoch全部正常完成；seed201/202各44评估和评分完成；seed203完成41/44物理、38评分，seed204完成42/44物理、39评分，两评估和评分进程仍活跃。之前03:45“首两臂训练中”已过时。

最终用户目标仍为现实尺寸刀具上的Wuji学习策略完整开合，经过可追溯论文参考/迁移实验、独立评估、可部署student与实际标定后真机执行。当前多seed只检验严格终止的收益是否稳定，不解决未见抓姿和未标定物性。该轮收齐后优先分析抓姿/接触及滑块阻力鲁棒性与物理参数假设，再冻结候选开展新独立验收；避免继续用重复seed替代真实迁移缺口。Sharpa是方法/实现参考线，GPU利用率是运行约束，均不替代Wuji实际任务成功。


## 自动更新：终止阈值seed20261204完整审计 2026-09-23T22:41:19.008128+00:00

两臂训练、44条件评估和Release上传已审计。分析 `runs/wuji-goal/diagnostics/termination-seed20261204-20260924-analysis-v1`；发布核验 `runs/wuji-goal/diagnostics/release-termination-seed20261204-20260924-verified.json`。均为已观察开发集，下一步读取两臂完整对照并冻结候选后另做新独立验证。


## 自动更新：终止阈值seed20261203完整审计 2026-09-23T22:47:04.333058+00:00

两臂训练、44条件评估和Release上传已审计。分析 `runs/wuji-goal/diagnostics/termination-seed20261203-20260924-analysis-v1`；发布核验 `runs/wuji-goal/diagnostics/release-termination-seed20261203-20260924-verified.json`。均为已观察开发集，下一步读取两臂完整对照并冻结候选后另做新独立验证。
