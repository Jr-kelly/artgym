# 当前任务的真机测力准备

实际平台是G2右臂7DOF＋Wuji一代右手20DOF。尚未连接/运行真机；离线模型检查不是硬件验证。现有URDF Nm限值与official_actuator仿真刚度未标定到具体设备/固件，不能据此宣称剩余推力。SDK effort/effort_limit以A表示，不能直接代入Nm负载计算。官方来源：[Wuji v1](https://docs.wuji.tech/docs/zh/wuji-hand/v1/overview/)、[SDK](https://docs.wuji.tech/docs/zh/wujihandpy/latest/api-reference/)。

默认入口不导入SDK、不连接设备、不使能和不发运动目标：

```bash
python -m scripts.prepare_wuji_singlepush_measurement --trajectory-audit research/singlepush-20261005/HARDWARE-FINAL-COMPOSITE.json --output runs/my-force-preparation
```

`poses.json`列出实际仿真轨迹起点/中间/末端的20关节测量、已发目标和7臂关节位置。它们用于对照记录，不能盲目作为真机运动指令。`force-log-template.csv`全部实测字段留空，状态为未执行。运行时先核验确切设备序号、左右手、固件、映射、真实位置上下限和effort限值；SDK手指顺序thumb/index/middle/ring/pinky，仿真顺序index/middle/ring/pinky/thumb。若仿真数组按5×4展开，SDK输出对应仿真分块[4,0,1,2,3]；下发前须按确切设备映射逐项核对，此入口不下发。可选`--read-device --serial <确切序号>`仅调用读取函数，仍不启动实时控制，不读取需要实时控制器的effort。

在已有授权的真机控制流程、相同抓姿和接触位置下，由现有控制器分别到达行程起/中/末，保留力计方向和关节记录。每个位置分别测滑块法向按压及沿导轨轴向推力：先校验力计零点、单位N及轴向方向，用独立法向/轴向装夹避免混合秤读数。以75gf=0.7355N为参考，再用1.0/1.25/1.5N已知负载；各位置至少记录1s持续值、最小/平均/峰值、位移、回滑、实际位置/命令/effort及effort_limit。同步拍摄完整过程。不得通过提高未知硬件effort限制弥补失败。

最优先缺口是相同姿态下持续输出的分轴实测，以及实际限位/固件位控刚度与模拟模型的一致性。15N标称指尖力不能替代此测量。缺工具时保留空字段，不造实测值。
