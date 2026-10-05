# 2026-10-06 接续说明

当前实际副本：`/data/research/artgym-experiments-20260921/contact-transfer-20261006`。
先读本目录 STATE.json、FINAL-REPORT.md、DELIVERY-RESULTS.json、REPRODUCE.md、
PUBLIC-DELIVERY-RECEIPT.json（发布后生成）。不得基于旧聊天摘要覆盖已有结果。
中央日志仍在 `/data/research/artgym-experiments-20260921/runs/wuji-goal/journal/events.jsonl`。
更新使用 `scripts.record_wuji_contact_transfer_event.record`，同步原项目续接文档。
不使用子代理；原项目代码与用户进程保留。最新Goal无利用率／最低时长要求。
PID与利用率必须按当前时间重新核验，不把历史记录当实时事实。

本轮完成具名映射、独立虚功／合成负载符号核对、SDK1.8实际接口与181条
仿真测量记录入口、通用可行前缀／接触与承托适配以及八项连续物理执行。
实际G2／Wuji未连接、未发运动指令；默认SDK适配器只读。

最强可用方案仍是singlepush既有actor+gain2路径跟踪、1.2N间接按压／0.1rad
按压偏移／0.2rad路径偏移设置。actor SHA256
6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e。
标称1.25N精确复现24.366mm（trace与前轮完全相同）；新中间尺寸＋1.25N＋
1帧延迟／噪声22.123mm通过。没有新增更高容量证明，不重扫1.5N阈值。

near-small35mm只在名义路径末段失败，通用前缀选34mm，实际29.713mm通过。
补偿后位置目标凸包可能重叠，但不是实际姿态：完整61点实际姿态最小间隙
11.780mm、原关节限位检查通过；20.1s独立LP也无实际凸包相交。
严格限制抽象PD平衡目标的guard导致14.557mm，属于保守负对照，绝不能说成
当前握姿的硬能力上限。真机需核实固件刚度／限流与接触丢失响应；不得把仿真
PD或重力力矩叠加到SDK位控，也不能把A drivequantity说成Nm/接触力。
NEW mid实际姿态最小间隙13.411mm，thumb4边界有0.148微弧度数值超出；严格
1e−7rad测试如实留fail，不为该数值调参／改阈值。

large-high根因是初始侧缘着力和推进期间滚转／支撑协调，不是电机99%饱和。
自由腕姿会碰食指预压限位，有限腕姿暴露食指／中指近端干涉，证书拒绝。
固定腕姿全法向32.408mm、cap1.0，但旋转0.615rad超原0.6，而且参考23mm处
分支跳变需限速，仅诊断。cap-width*.2通用侧移路径证书/步长通过，cap99.93%，
但16.530mm／旋转0.999rad失败。NEW upper几何＋变化阻力／摩擦3.488mm失败。
不提高摩擦、扩大cap、降低实际负载或改标准追认。

本轮未新训练。不要重复已拒绝的无约束腕姿、同一全法向跳变、纯增压、
去support残差或相同支撑位移。后续若推进较大尺寸，可用已可达的偏置接触
路径针对承托／推进协调训练；训练实际含该几何和失败阶段，修旧128env
aggregate容量或先64env。不要只追加相同PPO更新。当前Goal停止条件允许基于
清晰机制证据交付，并未声称整个几何范围或真机工作已解决。

部署具体入口在 isaacgymenvs/deploy/wuji/sdk_hand_api.py，读取实际设备限位／
effortlimit、具名编码器，接受外部力计时间戳数据；实际effort需已有实时
控制器注入，缺失留null。SDK安装独立Python3.10，1.8.0；Py3.8的1.7.0
Annotated导入失败已记录，不升级破坏原Isaac环境。USBVID0483/PID2000本机／
SSH主机均无匹配，不等于其他位置无设备。实测缺：设备连接、轴／零位／限位、
G2臂反馈和运动授权、同握姿起／中／末两个独立方向>=1秒的力／滑移／位移，
先0.7355N再1/1.25N，以及真实卡槽起动／沿程阻力和固件响应标定。

视频均本轮新录完整22秒：八个运行×全景／近景／同步＝24MP4；包含失败。
私人Goal文本在GOAL.private.md，仅本地，绝不发布；原HTML／照片未改变。
小overlay继承已验证singlepush依赖；final-v1首次restore继承父PYTHONPATH，
因此不作为独立恢复结论。final-v2明确只用恢复目录及其rl_games进行代表性
1.25N复现，最终证据见RESTORE-VERIFICATION.json。无需重复大型旧依赖恢复／哈希。
