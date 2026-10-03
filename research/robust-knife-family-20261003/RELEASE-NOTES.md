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
- `release-manifest.json`、`SHA256SUMS`与 `restore_wuji_robust_delivery.py`：下载校验及空目录恢复入口。环境需要Python3.8、PyTorch2.1.0+cu118、IsaacGym Preview4/TacSL；SDK不随包分发，精确依赖及运行命令见RESTORE.md/REPRODUCE.md。

已在空目录恢复核对1258个冻结运行文件，连续仿真v66成功，600帧完整策略离线回放电机目标误差0；训练恢复保留Adam/RNG，但重建物理回合，不宣称PhysX状态逐位恢复。

未下发真机动作。真实SDK映射/单位/方向、压紧与接触材料、双向起动和沿程变化阻力仍需实物校准；桌面中央任意摆放取刀尚未实现。较早闭合历史的尺寸辨识是离线科研线索，尚未进入actor或构成真机/算法优势。
