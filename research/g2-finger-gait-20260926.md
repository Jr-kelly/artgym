# G2＋Wuji 一代：有界分指换握实验

从GitHub及本机相同277efe475f886904096839f55549c0e07528146b开始。分支feat/g2-wuji-finger-gait-20260926，实验runs/g2-finger-gait-20260926。保存旧成果；实查原训练88339活跃，4090余量足够，未新训练。动力学开发上限18次，独立A也计数；正式20次位置验收仅在新连续B/C均通过后追加。

动作顺序固定：滑块朝下平放→掌心朝下侧夹→空中翻掌→分指调整→必要搬运→冻结teacher/student。禁止桌面换握/端立/约束/过程状态写入/驱动滑块。物性、手部无重力、G2伺服与碰撞过滤沿用原基线；NaN关节力不当实测。

## 目标与坐标核算

V2真实翻掌末帧689：以T_world_hand的逆乘T_world_object，四元数xyzw，手物旋转与抓姿0/1/2分别差103.6009/103.4764/105.7409度。刀身中心在手坐标相差11.591/11.130/11.371mm，反向坐标的腕原点相差210.635/210.011/213.050mm，后者是绕远端刀身的旋转杠杆量，不能当掌内滑移要求。

控制顺序是index,middle,pinky,ring,thumb各4关节；接触统计是thumb,index,middle,ring,pinky，必须按名称转换。s[:20]为实测初始化q，s[20:40]为电机目标。实际运行targets包含臂积分补偿，reference_targets才是臂规划命令；手指两者一致。续接动作以最后实际命令为起点，观测读实测q。

本地G2直接操作证据：抓姿0的A-operation-up5-v63与A-g2-integral-v12在20秒固定5秒换向下通过10mm/2mm/稳定；抓姿1的A-grasp1-table80-v47也通过，但桌高80cm与本次75cm不同。抓姿2仅存在早期原手固定场景证据，当前不升级为本次可接管候选。选0、1至多两种有证据的旧终点，几何差距无明显优势，暂以0为参考；当前侧夹只证明握持/翻掌，不称可操作。

D01独立A：抓姿0置于实际翻掌末腕姿，保留原闭滑块/物性，测试是否无需搬运即可操作。该初始化只在首次物理步前，绝不计连续获取。旧日志无完全相同腕姿，故需要此对照。

## 最小动作与判据

原样保持可复用V2翻掌后2秒真实保持；另在每个新试验起始加1秒同样保持门禁。优先保持拇指、食指、无名指、小指，仅中指卸载4mm。末态食指有刀背支撑，其余主要侧接触；组合能力仍须物理验证，不能假设拇指无名指两指独立足够。

若卸载成立，再中指绕侧下角迁移到底面，建立接触后保持1秒。其余16个电机目标及腕目标完全不变。各运动1或2秒、每段停稳1秒；2rad/s规划限速，首帧从上次命令连续开始。刀具目标为换握开始时固定世界位姿，整个单指流程不刷新参考。每段记录世界与手内位姿差、真实支持指位移、各指接触、滑块被动位移、首次10mm/0.25rad越界时间。接触点由碰撞网格估计，电机目标预压不能当实测力。

冻结策略操作仍按20秒每5秒换向，各段末0.3秒最大误差<10mm，2mm另报，接管世界参考漂移<10mm/0.25rad、无掉落。未进入策略记未评估。两种有物理区别的最小动作同样失败且无新解释时停止扩张；开发耗尽也停止，完整保留失败。

结果与复现命令随实际运行补充。最新进程状态以实验目录process/trace/report、journal与实查为准。

## 已完成开发记录（持续更新）

D01是未进入物理的A初始化IK分支拒绝，仍保守占用1次预算。D03加测得臂关节作为**独立A初始化**IK种子后，原限位内可达；teacher在当前实际翻掌腕姿下20秒通过：四段端点误差0.5625/0/0.2524/0mm，世界漂移7.122mm/0.13993rad。只证明该腕姿配功能抓姿可操作，不证明侧夹末态可操作。

D02原样保持→仅中指卸载4mm→1秒保持通过，卸载后中指接触为0，其余四指接触保留。D04再仅中指经外侧角迁移至底部并保持1秒，通过，世界最大2.962mm/0.07431rad。D06在D04后只卸载无名指也通过：5.382mm/0.12752rad；无名指无接触，拇指/中指/小指保留，食指保持段接触率80%。这些都是同一个固定摆放和相同获取前缀的开发对照，不是独立样本成功率。

D05在D04后做5个1度的小步转腕，各指补偿基座运动以维持固定接触；几何接触残差<1um，动力学第5度失败（固定参考4.276mm/0.30298rad），中指接触丢失。前4度未经最终保持检验，不能称已获得新的稳定终点。没有改变增益、质量、摩擦或稳定阈值。

D04及更早记录只保存接触法向/碰撞对，接触点来自网格估计；D05起确认PhysX字段是localPos0/1后才保存真实接触位置。不得将D04网格估计写成实测接触。电机目标减实测位置不是夹持力，未支持的NaN力矩不参与判断。

D07：D06成功前缀后，只移动无名指到底部。原接触纵向z=-22.3mm处底面IK误差2.27mm，拒绝；20个明确离散几何点筛查显示z=-12mm可达，选择外侧避让→底部→保持。D08：独立比较D04支撑下只释放拇指4mm并保持，检验是否已可直接迁移拇指。两次均从桌面初态物理执行，未加载规划源末态。

新审计脚本analyze_g2_gait_contacts输出逐阶段实测关节速度、限位余量、实际接触点/法向、滑块被动位移及手内目标偏差。所有保持沿用整个换握起点的固定世界参考，未在每个指动作后刷新。


D07完成：无名指底部新接触保持1秒，末段5.378mm/0.11839rad；全过程最大值另由逐阶段表报告。新支撑包括拇指/中指/无名指/小指，食指接触间歇，不假设所有四个非拇指都独立在承重。

D08的“stable=true”只表示刀身保持，**未完成拇指卸载**：卸载后1秒拇指接触率100%，小指0%。原在线门禁没有检查指定手指离触，现已补充；原文件不修改，汇总审计另外判定requested_contact_condition_met。D02中指、D06无名指的离触由原记录确实满足。

进一步检查发现中指底部末态的真实拇指接触材料点在刀身y≈-1.15mm，原网格极值点y≈-4.32mm。D10保留D04支撑、4mm位移及1秒时长，仅将卸载规划锚点替换为真实接触材料点；采用同一实际执行前缀D07的第989帧生成规划。只读取轨迹，绝不加载物理末态。该假设仍待物理验证，不把几何锚点偏差当作已证实原因。

D09从D04已稳定的中指换位末态直接接冻结teacher，检验是否真的必须再大幅换握。接管姿态未强制变为缓存姿态；目标仍为原slider_lower+0.04/0，固定5秒时钟两轮，实际50帧停稳历史和一次RNN归零，动作初始参考取实际最后命令。不会把该试验中的被动滑块位移当策略伸缩。


## 配置、接口及重现

冻结teacher SHA256 `4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac`；student `022ad8c7b3af18e25681fcd4073c1b48858621470293036df0311c488068e0f5`。后者本轮尚未使用，不改权重。手部重力关闭、G2臂重力开启；既有臂位置伺服kp=1000、kd=20、积分增益1（积分限幅0.08rad）；手部驱动取冻结配置。刀身29g、滑块6g，手/刀摩擦参数1/3，滑块零位置刚度、阻尼0.3、摩擦0.001。尺寸147×19×8mm，按钮30×10×3mm。物体无约束、无外力，状态仅首次物理步之前初始化。

G2自碰撞过滤沿用资产；D03新腕姿21个采样帧、D07连续路线91个采样帧的414对非邻接臂/掌凸包未检出重叠。此检查不覆盖近邻连接壳体、右手指间和采样帧间，不代表真机标定。实际物理记录的手指/桌面接触单独保存。

D09接口离线回放全部600帧：观测、action和电机目标最大误差均0，固定初始参考未刷新；50帧实际settle_history，历史零action对应实际电机保持，RNN只在接管归零一次。该检查只验证执行与接口一致，不能证明抓姿适合teacher，也不是新物理成功。Teacher实时读物体/滑块仿真真值；Student接口则仅使用q编码器、q的FK指尖、执行动作历史、固定几何、目标时钟和接管时一次初始物体位姿（当前只能标理想真值初始化）。Student未运行，不能称部署成功。

实际获取的滑块处于原lower=-0.032674588m，D09接管未重置滑块，也未修改目标零点。两轮操作目标lower+0.04、lower+0、每5秒换向；两次伸出/收回总20秒。D09掉刀，C及新10位置B/C配对20次验收不启动。

独立实验命令（必须用新name，保留已有输出）：

```bash
cd /data/research/artgym-g2-tabletop-20260925
python3 -m scripts.launch_g2_trial \
  --run-root runs/g2-finger-gait-20260926 --name NEW-B-middle-bottom-teacher -- \
  --group B --operation-yaw 90 --yaw 180 --dx -.05 --wrist-posture -.7 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan assets/robots/g2_wuji/plans/edge-pinch8-slider-down.json \
  --slider-face down --table-localization settled-truth --air-flip 180 --lift-height .30 \
  --gait-plan runs/g2-finger-gait-20260926/middle-reseat-v2.json \
  --stay-after-gait --video --camera hand
```

上述只是D09重现入口，不是追加预算。完整逐次命令在各`*-process.json`；新增Release的增量证据保留运行源码覆盖层、输入计划、物性、原始轨迹、contacts、日志、失败以及全部源码SHA。Release解包后可恢复任一精确源码版本，以下只准备文件，不运行物理：

```bash
gh release download g2-wuji-finger-gait-20260926-v1 --repo Jr-kelly/artgym \
  --pattern 'g2-wuji-tabletop-evidence-finger-gait-v1.tar.gz' --dir /tmp/g2-gait-release
tar -xzf /tmp/g2-gait-release/g2-wuji-tabletop-evidence-finger-gait-v1.tar.gz -C /tmp/g2-gait-release
gh release download wuji-experiments-20260923 --repo Jr-kelly/artgym \
  --pattern 'wuji-core-teacher-student-20260924-teacher.pth' --dir /tmp/g2-gait-model
python3 -m scripts.restore_g2_evidence_trial \
  --evidence /tmp/g2-gait-release/g2-wuji-tabletop-evidence \
  --trial D09-B-middle-bottom-teacher --destination /tmp/g2-gait-d09-source \
  --python /home/agiuser/miniconda3/envs/artgym/bin/python \
  --teacher /tmp/g2-gait-model/wuji-core-teacher-student-20260924-teacher.pth
bash /tmp/g2-gait-d09-source/reproduce.sh
```

重现需要已有IsaacGym/ArtGym环境；运行从桌面重新开始。恢复的只是源码和电机计划，从不加载旧物理末态。代码和原资产基线为277efe475f886904096839f55549c0e07528146b；每项实际运行SHA以SOURCE_SHA256.json为准，不能拿最终源码冒充旧运行版本。

两台此前开发机10.14.0.106/.93端口30147本轮实查均拒绝SSH连接；本机已完成可用仿真，交接同步本机入口和GitHub，未改远端或原训练。
