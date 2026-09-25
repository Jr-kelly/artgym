# G2＋Wuji 桌面取刀→伸缩（2026-09-25）

分支 feat/g2-wuji-tabletop-20260925；工程 /data/research/artgym-g2-tabletop-20260925；实验 runs/g2-tabletop-v1。当前资产审计/建模阶段，未进行新训练。

任务：固定刀具、固定正常桌面摆放、一个功能抓姿；G2右臂接近/闭合/抬起/移到操作姿态；同一仿真连续状态接冻结teacher再student。模型源 /data/research/ArtBot/G2_crsB_wuji/robot.usd，禁止套用Franka安装或参数。

A预置→teacher；B实际抓取→teacher；C实际抓取→student。先A定位场景/接口，再B定位抓取末态/接管，最后C初始化/历史。无瞬移/缓存重置/物体约束/隐藏外力/驱动滑块。20秒操作，每5秒按外部时钟换向。保留原手/刀物性和冻结权重，新增机械臂驱动与碰撞单独审计。

接管记录测量q、实际命令target、固定物体/手初始参考、清零RNN；历史仅来自执行数据，可用停稳积累50帧。student物体初始位姿若读真值标记理想初始化对照，不宣称可部署。

固定场景接通后先冻结代码/参数/抓姿，再确定seed和20个小范围位置/朝向偏移；全量保存失败。分报抓取、条件伸缩、整段成功；10mm端点末0.3秒、2mm诊断、刀身10mm/0.25rad稳定与掉落分列，参考固定在接管时。

交付新分支/新Release、运行命令、完整无文字视频/失败视频、轨迹和分类，不覆盖旧结果或历史备份。原4090训练88339保留，运行前重查显存；仅进行有用仿真，不为占用GPU启动无效计算。

下一步：导出G2结构与右臂URDF（复用原Wuji手），纯观测/动作接口核对与A实验；已有USD中部分joint child frame非identity，需要完整 T_parent_joint @ inverse(T_child_joint) 转换。

## 17:13 CST 进度

整机88链接/87关节已导出；右臂7+右手20活动关节，其他固定。安装偏移34.1mm/Rz(-90°)，无Franka参数。原手URDF哈希保留。几何审计table_grasp_geometry.json：3抓姿slider朝上穿桌40–44mm，朝下更差；直达功能抓姿不可无碰撞取得。A-source-gains-v1已完成但失败：8mm行程、右臂和刀身漂移；原增益100/1、重力开启。A-servo-v2正测试1000/20；A-gravity-diagnostic-v2关重力仅定位，不当正式方案。interface-v2证明初始观测与原环境最大差1.2e-7、动作8.94e-8；student init必须使用raw _get_init_obs（actor prefix另做frame/hemisphere转换），已修正在新代码。所有新试验由launch_g2_trial复制独立source-pins运行。

## 17:21 CST 初始化问题定位及A恢复

A-original-fixed5-v1在原环境20秒所有端点2mm/稳定均成功。A-initialization-handonly-v4仅将episode初始化移到prepare_sim之后、首次simulate之前，并首帧按原at_reset_ids语义组观测：10秒39.5mm行程，端点2mm/全程稳定通过。此前A1–A3失败不能作为改物性必要性的证据；均保留为初始化错误对照。G2 V4操作姿态改world yaw90以远离第7关节限位，保持腕部重力方向不变。A-g2-initialized-v4（手/刀原物性、右臂1000/20）、A-g2-source-gains-v4（右臂100/1）正在20秒操作，均已一轮成功。B-direct-grasp0-v5开始真实正常桌面抓取，首次控制前初始化为开手+平放闭刀，此后禁止状态写入；实际抓取失败将跳过策略接管，不伪造C结果。命令参考各-process.json，源码pin独立。

## 17:32 CST 续接与结果汇总（时间纠正）

A-g2-initialized-v4成功：20秒四端点全部2mm内，40.019mm行程，世界漂移8.450mm，手内4.855mm。有效原G2驱动100/1对照A-g2-source-gains-v4也全部端点成功，但世界漂移79.714mm，因此新场景暂用右臂1000/20（仅仿真伺服调整，未硬件标定）；手刀参数不变。
B直接抓姿0、侧滚yaw180的抓姿0/2高度+15mm和0mm共5次真实抓取均未抬刀，操作跳过。两个yaw0侧滚候选IK失败单列，不计物理成功率。详细目录B-direct-grasp0-v5、B-rolled-yaw180-grasp{0,2}-v7、B-rolled-contact-grasp{0,2}-v8。功能抓姿支撑指需进入桌面下40–44mm；侧滚−75度仍有14mm穿桌，抬高则错失接触。下一步有限尝试侧向上缘夹持，再真实抬起/就位，禁止隐藏重置。
student-interface-v8：50实际执行历史帧，输入最大误差1.19e-7、动作2.32e-6，改变实时物体真值不影响student输入。仅接口验证，未完成C实际抓取。无新训练、无20次扰动验收。原训练88339仍运行。

## 17:45 CST 接触几何诊断

新增plan_g2_edge_grasp.py，用所有手碰撞凸包顶点检查桌面约束，先求侧边触碰，再求开指/闭指电机目标。v9只约束最近顶点，实际主要压在上表面；B-edge-{direct-,}grasp0-v9均失败。v10加入有限关节积分伺服（gain1/s、限幅0.08rad，只调整驱动target，不施加外力），闭合接触仍未形成抬刀。所有实验独立source pin、旧失败保留。
法向侧夹v11要求指端支持面位于刀身两侧，几何桌面净空0.63mm；真实v11仍未抬起，怀疑闭合目标仅约0.8mm预压不足。v12允许4mm电机目标过行程（实际指头由接触阻挡），正在物理验证。同时A-g2-integral-v12确认新伺服不破坏冻结teacher。普通姿态roll0法向侧夹候选thumb误差21.7mm，几何不合格，不启动该物理试验。
DOF传感器接口返回False，当前TacSL IsaacGym不支持该actor的关节力测量；v10/v11力数组无效，不当实测。v12起以NaN明确不可用。轨迹审计证明G2腕部FK与仿真一致约1微米/2.4e-6rad，已完成路径关节限位及命令速度无超限。碰撞计数从get_env_rigid_contacts记录手指-桌面/刀具配对。

## 17:54 CST 抓取子阶段首次通过

B-pinch8-transport-grasp0-v14从正常桌面连续抓起，完成20cm抬升、搬运及停稳，grasp_success=True。只改变手指闭合目标预压4→8mm，未改手部增益/摩擦/物性；该8mm是求解电机目标时的虚拟过行程，实际手指由接触阻挡，绝非写入刀具/手的物理状态。原4mm版本能抬升但搬运时长轴下倾后滑落；v14夹持通过，尚未操作。B-pinch8-teacher-grasp0-v15正在跑冻结teacher完整接管对照。
A-g2-integral-v12新伺服复测：40.090mm行程、四端点2mm均过、世界漂移7.744mm、旋转0.1498rad，全程稳定通过。
简单手指插值就位B-normal-seat-grasp0-v13抬升后掉落，视频/轨迹保留。尝试保持刀具长轴近水平的B-pinch4-level-grasp0-v14在抬升后规划发生IK解分支跳跃，被连续性门禁中止，保存partial-trace；这是搬运规划失败，不是物理抓取失败。暂不扩大该路线。
plan_g2_seating.py生成接触保持的腕部+手指路径：固定腕部插值v15中间接触误差达15.5mm；加有界腕部位置调整v16全部接触几何误差<0.1mm。B-contact-seat-grasp0-v16正在真实自由物体仿真，先抓取再8秒就位；没有物体约束、位姿写入或滑块驱动，几何可行不等于物理成功。
仍未训练、未做C真实操作或20扰动验收，未发布GitHub。下一步收v15/v16结果定位策略接管与手内就位；不要把首次抓取成功写成完整任务成功。
