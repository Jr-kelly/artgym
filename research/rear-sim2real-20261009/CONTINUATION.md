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
