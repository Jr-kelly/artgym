v4自研源码已同步：local 0e3912d5afa4017aecad17b4660403cf33a26780 ↔ GitHub 6de142585c08a4254f23d62cde14612afed3c4df，相同tree 78e63a8cdaca44644e473960da339813eb489606；旧两分支未改。私有交付包与现场指南留私有目录，未公开。完成范围是独立软件准备，hardware_deployment_complete=false；后续仅具体现场事实，不能默认重训。

# 当前v4：制造商接口整合

软件实际克隆/包核查/实现/离线协议与组合会话已推进。当前bundle-deploy-v9.json；先读v4/REPORT.md和STATE.json。私有制造商源码、包、详细现场指南、原始日志留在独立私有交付；公开源码只有自研IPC/会话接入和脱敏结果。

选择现场同机Wuji SDK 30Hz＋独立CoRobot右臂轨迹/point保持；GDT真实PolicyServer做状态查询，reset拒绝，受载期间不进入PolicyTaskServer。require_g2不再无条件阻塞，而是校验桥接pin、实际包和现场事实，再由真实反馈建立到位/保持；没有假ready或空接口。

21项最终协议合同、1175帧组合fixture（p95 8.865ms/max13.632ms/零超33ms）与24项旧合同、380帧0rad差异通过。没有新增物理仿真，因为手核心、发令和归一化不变；v3物理成功与延迟/刚度失败均保留。real_robot_ran=false；硬件状态/控制权/安装/保持过期必须现场核实。

集中待取得实际G2/Wuji/固件与标定安装对应、工具只读capture与网络配置、Wuji USB独占和右臂单写/point过期语义。不能默认启动训练或矩阵；也不能把状态RPC服务称为GDT动作部署完成。

<!-- V4_HISTORY -->
最终分支回执 local bc0fe328aef4be8b8b4583a5a7ded6b4ff8a091a ↔ GitHub b5c08cdab4b1a459d0932a5d6e7e6b4286598340，tree be46156b75e7d83f079f6fdf3bd43981d98d5e2e完全一致。原生goal complete仅表示本轮可独立完成的软件／必要仿真／包／发布完成；hardware_deployment_complete=false，G2真接口待最少现场资料。

v3离线交付及公开下载已完成：https://github.com/Jr-kelly/artgym/releases/tag/wuji-rear-sim2real-20261009-v3。科学源码 local bb968a1cdb531c7ef7987f815e75b73241639dfb ↔ GitHub 5fdb08d21a1af1ce63c0d311e10e5b9cbeb90375，tree ec764dd962f91b130df2347371a665bf987c0688一致。最终分支还保存发布回执；G2接口与所有真机结果仍阻塞/未测。

# 当前接续：rear-sim2real v3（完整部署调用链）

实际副本与分支不变。当前 bundle-deploy-v8.json，500个模型/资产/配置/框架源码哈希。先读 v3/REPORT.md、FIRST-HARDWARE-SESSION.md、v3/STATE.json。现场统一field.json与wuji_rear_field入口；一个当前包＋已有基础一次恢复，无需依次覆盖v1/v2。当前真机session明确拒绝G2缺项；没有空接口/mock到位证明。

已实现连续Wuji连接／已发目标／response→后台分析→probe，probe后卸载并30mm复位再摆放／新历史进入fullpush；重启必须确认卸载，正常结束取刀后请求disable。绝对零位独立证据导入，小动作只验证轴；命名限位/速度不兼容拒绝，速度不足不放慢全段。真实SDK1.8.0无模式/使能读回，ACK不等于物理状态。G2_t2_crsB只是资产线索，本地G2A CoRobot应用对应SDK未安装，两者不能推断这台实机接口。

仅新增1条共享RearSession物理全段：32.420mm、保持1.033秒、末1秒波动.0277mm，有限执行器/被动阻力/撤托、无刀状态恢复和真值控制。原一帧延迟等失败保留，无训练、无矩阵。开发机新绝对路径实际加载模型与SDK子进程，24软件检查通过，380合法输入指令0rad差；1174次组合fixture写入p95 6.761ms/max11.850ms，无超33ms，不代表现场时延。旧约64ms尖峰失败保留，GC暂缓后的改善只作关联证据。

默认没有实验作业继续运行。需要现场的最少G2资料集中在指南末尾；所有实际设备零位/模式/速度/固件保持、时序、受载响应与>20mm/1秒仍待现场。real_robot_ran=false、hardware_deployment_complete=false。旧取物/换握用户修改和protected分支保留。发布回执见v3目录（完成后），最后应核对远端与本地相同tree和全部Release公开下载哈希。

<!-- V3_REAR_HISTORY -->
最终v2源码同步：local aabc3d139db917ffe8a8219c7ba10f6fd98c55dd ↔ GitHub 5d80eaf9f66fb38176aee04403136ecc1ba46d4b，相同tree 74938a1da588e96515c6a957609c40f8a2c82dc3；旧两个分支未改。原生goal complete范围是全部离线交付，真机未运动。

离线交付已完成，公开Release：https://github.com/Jr-kelly/artgym/releases/tag/wuji-rear-sim2real-20261009-v2。本轮默认v7，真机未运行。

# 当前接续：rear-sim2real v2（短试推与现场响应诊断）

沿用当前同一独立副本 `/data/research/artgym-experiments-20260921/rear-sim2real-20261009`，分支 `feat/wuji-rear-sim2real-20261009`，未回退旧12c2894外部审查提交。先读 `v2/REPORT.md`、`FIRST-HARDWARE-SESSION.md`、`v2/STATE.json`，当前默认 `bundle-deploy-v7.json`；v6与v1 Release是历史固定证据，恢复旧源码再用旧pin，不可把旧哈希硬套新源码。

v2只新增3条物理仿真：标称短试推4.5145mm（误差−0.4855mm、末1秒波动0.0273mm）通过；仅一帧延迟−1.8782mm失败，动作0.8667秒先滚转、1.1667秒持续失接触；同现场受载response1秒基线＋2秒0.01rad拇指第二关节往返＋1秒恢复，承托成立。短试推保留完整35mm目标与前4mm时序1.0398秒，随后0.1943秒平滑减速至5mm参考，1.2341秒转保持，不减慢整段、不读取滑块真值。新视频v2/review.html，两条380帧同步远近视角已抽取关键阶段核对，仍不把抽帧称为连续GUI播放。

算法复用旧标称／低刚度／延迟任务日志并比较：闭环与接触变化使机械延迟无法可靠辨识；新弱单次响应也不给可靠毫秒值，只保留描述拟合、采样分辨率与原因。位置幅度、静态变形、去偏置动态误差、主机各段耗时均分开。丰富离线已知偏置／0或1额外采样步测试通过，不是物理实验。profile v2明确位置记录／有界试推许可／力未标定／完整可靠性未建立。SDK fixture分别明确，完整loop含日志的统计及每帧timing关联通过，新增只读字段核对读取实际SDK时间窗口。真机发现[]，无真实运动。

当前完整控制重放旧380帧发送目标零差异、标称短试推减速前与旧完整物理命令也零差异，完整控制参数未变，未重跑整段任务／矩阵。原32.420／28.447mm和接触0.35mm边距、刚度／延迟失败继续有效。未训练、未做前半段、未建子代理。保护原用户修改与取物／换握副本。

下一步仅需现场的真实响应数据、尺测短推／保持、近景接触与侧面滚转视频、固件限位和原始时间戳。按guide从discover/read开始，现场首次使能与明确运动授权后检查20关节、hold、response、analysis、临时补偿profile、probe；短推失败不继续fullpush。位置日志无法辨识真实力、全部K、摩擦或纯USB时延，不宣称sim2real解决。不默认增压、训练或追加同质实验。

v2公开增量依赖v1已验证根；旧模型／资产复用，当前343个依赖哈希在v2/DEPENDENCIES，实际冻结sha 47709399dd02874cebdd7766f263738bb1b9a315d4bd00fe1d5c2e41f4badef2。v2同步／Release／完整公开下载哈希回执均在v2目录；v1旧回执保留。私人附件未复制到公开材料。

本轮实验进程已结束（UTC 2026-10-08T20:35:21.312542+00:00）；上述PID和GPU单次11%是开始时快照，不作为当前或四小时合规事实，接手要重查。用户monitor和原视频server继续保留，无填充计算。

<!-- V1_REAR_HISTORY -->
# 固定握姿后段：续接入口

实际工作根 `/data/research/artgym-experiments-20260921/rear-sim2real-20261009`。本轮完整读取私人附件并直接执行，附件未公开。原项目用户修改、训练与 `flat-table-20261006` 取物／换握全部保留。本轮没有启动大规模训练，没有子代理。

已完成共享闭环后段＋独立SDK进程、真实可行的人工摆刀／撤承托／50帧实测历史／隔离预热／新历史接管；源码、资产、权重、归一化与参考绑定在 `bundle-deploy-v6.json`（340项依赖 SHA256，文件自身哈希见 DEPENDENCIES）。先读 FINAL-REPORT.md、FIRST-HARDWARE-SESSION.md；本地视频 review.html。

最终同入口仿真：标称0.7355N主动32.420mm、1.25N主动28.447mm，均独立支撑并保持约1秒。v3温和摆放／单独估计／被动局部卡顿已通过，最终v6联合执行器误差仍失败（−1.17mm，7.5秒先滚转）；v4节奏与v5支撑反馈两种修正未改善联合失败，保留开发证据、未推广。已停止同机制搜索，不能凭静态持刀宣称动态迁移成功。无实时刀位姿／滑块／接触真值输入。

冻结软件11项契约、380帧指令一致性、小行程probe SDK模拟对象470帧及故意破坏依赖的拒绝检查通过；这不是硬件连接、接触仿真或现场时延。真实SDK1.8.0导入通过，USB发现[]，零真机电机命令。raw完整循环统计见 ENTRY-VERIFICATION。硬件实际effort仍不可读，力计驱动与G2动态臂后端未接入；不宣称力标定或最大推力。

下一步只能现场：连接一代右手／原装供电USB，固定图示腕向，现场协助首次使能；discover/read；20关节小动作核对方向零位限位并绑定device profile；按图摆刀hold／撤承托；response并绑定局部位置响应；probe5mm若无滚转滑脱，再push并尺测>20mm／1秒视频。SDK子进程使用现有Python3.10，推理沿用Python3.8 Torch2.1，不升级环境。发现USB不等于真实运动授权。

公开新增分支 `feat/wuji-rear-sim2real-20261009`，Release `wuji-rear-sim2real-20261009-v1`；实际commit／上传校验回执见 SOURCE-PUBLICATION、RELEASE-VERIFICATION。与已有contact-transfer、flat-table分支比较时不可混淆不同初始化与版本。归档分出运行增量、原始证据与本地可播放材料，旧权重复用；恢复核验不算新增物理成功。

资源快照 UTC 2026-10-08T19:57:46.618805+00:00（上海+8）：本轮实验进程已结束；用户monitor97337/580871/760633/3132243、视频server4098仍保留。单次GPU读取14%，不据此声称4小时门槛满足；未运行填充作业。接手必须重新验证进程和利用率。之后无新证据时不要默认追加PPO或同质短仿真。

离线交付已完成 UTC 2026-10-08T20:01:28.076514+00:00。初始发布源码 local c99d1d93db6127b229f70d6c770277f0d8854fe6 对应 GitHub ac0b0c9941d86e00589f83756ba444e8d1612046，完全相同 Git tree 851c8dd23805b45e5a5ddad25d1fa584bd6f6020；最终分支包含上传回执。Release已公开：https://github.com/Jr-kelly/artgym/releases/tag/wuji-rear-sim2real-20261009-v1，五个资产全部经服务器digest及不带凭据的完整公开下载SHA256双重校验。残余工作仅现场，未执行真机。

最终源码同步：local 155de352393cc72a5bec349bcf216fb15d9538b5 ↔ GitHub 12c289470cb1c7aaac9eaca2be5c918fd8ffdcae，Git tree b65c64e5b9fb2ab531bd324c5eac64736966d45d 完全相同；原两个分支未改。原生goal已标complete，完成范围是附件规定的全部离线开发验证／首次现场材料；real_robot_ran=false。下一轮只有新现场信息或具体新证据才推进。
