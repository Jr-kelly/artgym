# 单次伸出新Goal续接

独立副本/data/research/artgym-experiments-20260921/singlepush-20261005；分支feat/wuji-singlepush-20261005。旧newknife结果保持不变。完整Goal已读，私人附件不公开。新控制时钟16s前同实际取刀/换握，16s单次伸出，之后一直保持，不执行回收。先建立基线，再推力余量、必要新冻结泛化、具体硬件核查，最终GitHub交付。禁止子代理，未授权真机动作。

## 已完成和当前工作

所有结果是原始仿真，不是真机。正式22s取刀→35mm单次命令→保持基线位于 runs/singlepush-20261005/baseline/nominal-reference-v1；十项新判据全部通过，主动位移27.6675mm，保持波动0.0373mm。660帧双机位同步完整视频 singlepush-synchronized.mp4 已制作且检查画面。

固定nominal几何仅更改被动容量：1.0N基线通过23.3015mm；1.5N仍全程cap接触但只有11.1769mm。calibration/force-levels-v1的0.7355/1/1.5N隔离校准都通过，不是硬件测力。实际轴向总接触力缺可靠通道，不重复错误接口。增压、仅操作增压、压力投影、raw轴向偏置、Cartesian轴向偏置、Cartesian法向解耦均未提高有效推进，接触/承托失败证据在development，不可选为最终方案。不能宣称力矩不足，未达模型限幅。

几何28mm完整物理：small有效19.125mm(取刀先滑10mm，不能计入主动推进)，middle15.315mm，large无推进且cap接触18.945%。large在17s后丢cap，18s开始短暂触及固定刀体，指腹原先靠滑块侧缘。small原失败是从0.35mm开始的无用pickup姿态全行程；正确gate为pickup保持0，真实换握后全stroke独立证书。small-postlift28-v2已完整通过规划并执行，small35-v3正在准备。旧heldout全部转开发，不作新冻结验证。

当前远端 /home/wangjiarui/artgym-singlepush-20261005 的3作业 adaptive-hold-load-{0.73549875,1.0,1.5}-v1 使用原1.2/.1配置，在20.033s后仍保持合法反馈而不锁死目标，原向前goal不变；这是持续输出对照。large-support0-v3单项去掉学习support残差用于区分名义几何与支持动作失配。PID接手必须核验。

HARDWARE-COMPOSITE-v2.json补齐实际轨迹采样正常p05/mean/peak×轴向0.7355/1/1.5N+拇指重力/惯性；最紧模型关节thumb2，峰值法向+1.5N约38.1%URDF限值，不能当成真机余量。SDK单位A非Nm；本地无SDK/USB设备，默认不运动入口和起中末分轴测力CSV在hardware/measurement-baseline-v1，hardware_verified=false。

下一步：核验当前结果→只留有改善的方案→冻结几个未用联合case→代表性复现/视频/GitHub。私人GOAL.private.md永不发布。独立record_wuji_singlepush_event维护本STATE和中央journal。

## 冻结实施与验证已完成（待发布/恢复收尾）

最终改进已生效：reference-path-drive.json沿原IK路径切向使用测量关节跟踪误差，gain2/maxdistance15mm/maxjoint.2/filter.1s/ramp0–1s，原压力1.2/.1和实际执行器不变。固定H200原baseline1.25N仅19.159mm失败，最终24.903mm通过；1N23.302→28.289mm，1.5N11.177→19.874mm仍失败。不要因19.874四舍五入宣布通过；不再继续增益扫描。

4090最终原始完整视频：final/local-reference-video-v1主动29.470mm/保持.027mm；local-125-video-v1主动24.366mm/保持.033mm；local-150-video-v1仅18.545mm失败。所有完整660帧双机位同时间，compose工具独立新命名，不执行回收。remote H200尝试视频在图形初始化SIGSEGV，之后切回已工作的本地4090，失败目录不作为任务结果。

两个新冻结联合near-large/shift-delay通过28.531/31.203mm，near-small实际35mm路径只有最后一点自碰撞间隙−.0395mm，未执行；冻结后不改规则。开发small35/middle35用同最终路径控制通过30.472/25.731mm；large失去cap接触仍未解，不宣称全部范围通过。FROZEN-CANDIDATE.json、NECESSARY-FROZEN-CASES-v1.json、FROZEN-JOINT-RESULTS.json记录统一actor/recipe、哈希和隔离分组。

HARDWARE-FINAL-COMPOSITE.json基于最终1.25N轨迹，全合成最坏情景44.24%URDF；实际thumb4达位置边界，不能称真机自由余量。默认非运动入口已执行measurement-final-v1，SDK未装/ttyACM空/运动命令0；具体测力步骤HARDWARE-MEASUREMENT.md。real_robot_ran=false/hardware_verified=false/B轴向总力缺测。

当前任务只剩交付复现：从两个既有wrap归档加singlepush小覆盖包恢复一次22秒仿真，生成可浏览视频report.zip，发布授权新分支feat/wuji-singlepush-20261005与Release wuji-g2-singlepush-20261005-v1，验证服务器SHA和一次公开下载。源GOAL.private.md始终排除。当前源码尚未提交；不要发布整份私人Goal。

最终待发布覆盖包为release/final-v2/singlepush-overlay.tar.gz，SHA256 972336ac1d8f66a3509c726e45b3da2db36a68c877a58c108979c8cb5d46cf85。restore-gate-v2从空目录1481文件校验并运行22秒，通过29.4699mm，原最终视频trace SHA完全一致。初版restore metadata沿用旧文件名的错误已修，最终覆盖包含修复。没有遗留实验GPU作业；发布代码/包/视频并验证公开下载后关闭交付状态。
