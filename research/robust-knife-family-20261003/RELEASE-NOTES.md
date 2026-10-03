# G2 + Wuji v1：桌缘取刀与带阻力连续伸缩

完整连续仿真已做成：135×16×12 mm主体（厚度不含滑块、无需按下解锁），从指定长边桌缘取刀、持稳，连续完成两轮伸出、保持、缩回、保持。操作采用已训练P50有界残差与名义滚动拇指参考，取刀前缀为脚本/离线规划；这是学习混合控制。

必要泛化仍未解决。预先冻结的同一策略、同一原成功标准，全部332独立联合随机化回合204通过；83刀身失稳/掉落、44取刀/持稳失败、1缩回失败。新128几何78/128，较高负载新前64为36/64；厚13–14 mm、滑块高度+1 mm和较大变化阻力仍有明显支撑缺口。冻结后条件稳定性和额外训练另行标识，不并入主成绩。

名义完整成功v38/v55使用工程运行/起动幅度各0.2 N、变化脉冲负载，记录附加峰值约0.46 N；操作期真实拇指–滑块接触100%。0.5/0.5 N代表性应力失败保持原记录。0.10 N不是实物阻力上限，关节位置偏置/求解器lambda不是恒力控制。

- 观看 `continuous-demo-success-and-failure-v2.mp4`：完整36秒成功与完整36秒失败，各有同步全景/近景，2160帧均来自保存的实际回合。
- `wuji-g2-source-final.tar.gz`：代码、配置、说明、证据报告；仅省去旧轮无关multigrasp证据目录，未修改冻结运行源码。
- `models-and-recovery-final.tar.gz`：R800/teacher、冻结P50、已评估候选及真实末次权重，Adam与CPU/CUDA/NumPy RNG。
- `independent-validation-all332.tar.gz`：全部独立初态、轨迹、结果及96条预选实际视频；失败不筛除。
- `continuous-demos-and-failures.tar.gz`、`restoration-execution-evidence.tar.gz`：完整连续成功、代表性失败与实际空目录恢复运行证据。
- `frozen-development-evidence-final.tar.gz`、`highload-paired-development-evidence.tar.gz`、`secondary-context-and-material-evidence.tar.gz`：单独的开发/机制研究，不是主独立成绩。
- `closing-context-adaptation-evidence.tar.gz`：单独155维闭合测量上下文原型，有限配对训练的两组末次权重、Adam/RNG与三组完整开发轨迹；未解决厚刀柄支撑，不替换主P50。
- `final-downloaded-recovery-evidence.tar.gz`：实际下载最终文件、空目录恢复后的完整连续仿真、600帧策略回放及全部七组固定332条件重执行；恢复重复与原独立成绩明确分开。
- `release-manifest.json`、`SHA256SUMS`与 `restore_wuji_robust_delivery.py`：下载校验及空目录恢复入口。环境需要Python3.8、PyTorch2.1.0+cu118、IsaacGym Preview4/TacSL；SDK不随包分发，精确依赖及运行命令见RESTORE.md/REPRODUCE.md。

实际GitHub下载最终源码/模型/资产已在两个空目录核对1258个冻结运行文件；连续v68成功，固定高阻力v69重现原失败，成功与失败各600帧完整策略离线回放电机目标误差0；训练恢复保留Adam/RNG，但重建物理回合，不宣称PhysX状态逐位恢复。

全部七组H200无图形恢复重执行为185/332，原4090录像验证为204/332；初态和前缀命令相同，接触轨迹仍有差异，高度组8/32（原18/32）。这是尚存可移植性限制，不替换主成绩，全部恢复轨迹提供。逐案例配对为182两次通过、125两次失败、22原通过变失败、3原失败变通过；不能只用总分相近说明逐案例可复现。

未下发真机动作。真实SDK映射/单位/方向、压紧与接触材料、双向起动和沿程变化阻力仍需实物校准；桌面中央任意摆放取刀尚未实现。较早闭合历史的尺寸辨识已接入单独155维开发原型做有限配对训练；它不替换原冻结P50，尚不构成真机或算法优势。

接触过程的 12 面板图、原始绘图数据与解释见 Release 附件 `CONTACT-BEHAVIOR.md`、`contact-behavior.png` / `.pdf`、`contact-behavior-data.json`。高阻力失败先持续失去滑块接触，再越过刀身稳定阈值；记录的 30 Hz 样本未触及拇指电机限幅。这是过程观察，不是隔离因果结论或实物恒力标定。

最终结果以直接附件 `FINAL-REPORT.md` 为准，资源与十二小时时间门槛见 `FINAL-RESOURCE-AUDIT.json`。源码归档中的报告/续接文档是打包时的时间快照；本次标签和交付清单指向包含后续恢复核验入口与报告的最终 Git 树。继续工作应读取最新分支的 `WUJI_GOAL_HANDOFF.md`，重新核验 PID 和设备状态。
