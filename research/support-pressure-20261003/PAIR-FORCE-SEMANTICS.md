# 本轮实际仿真接触对力语义

安装SDK文档将RigidContact.lambda描述为Contact force magnitude。已知box载荷1.027840 N在240/480Hz、1子步，以及2子步last/all报告下均返回总lambda≈1.027840；不除以dt。这里每simulate调用仅1物理子步，240Hz采样后对8点求时间平均，空间接触点只求和一次。

夹具body0=box/body1=ground，normal向上；+normal*lambda与box净法向力一致，说明实测body0受+normal、body1受-normal。该符号与文档body0→body1措辞不一致，按已知载荷实测处理。旧夹具v1的signed_pair_vector是相反的符号假设，原样保留，不使用为正式压力。

拇指—滑块作用在滑块的法向合力投影到当前滑块局部+y的反方向，输出压紧力N。轴向输出只包含接触法向矢量的局部z投影，尚不包括Coulomb切向摩擦。无名指刀底支撑按刀身局部负y接触位置且正y反力筛选，保留实际位置。

所有当前接触、物体姿态和导轨位移仅用于评估，不进入控制/actor/触发器。夹具外力仅用于校验，没有给正式demo刀、滑块或手指外加辅助力。没有实物力传感或最大压力标定。

原生SDK文档另有lambda_friction但实际结构名lambdaFriction；当前未据此重构切向合力。相关[PhysX原始接触点说明](https://nvidia-omniverse.github.io/PhysX/physx/5.1.0/_build/physx/latest/struct_px_contact_pair_point.html)描述底层冲量，不代表Gym封装lambda仍需除dt。以本SDK夹具校验为准。


补充原生摩擦字段核查（v151）：安装结构中 `lambdaFriction` 是两个分量的Vec2。旧校准脚本检查了文档拼写 `lambda_friction`，因而不能用旧记录的零值判断摩擦是否被报告。使用正确字段重做一个240 Hz、1子步已知箱体夹具：水平外力0.15 N下箱体近静止，两个原生摩擦分量仍全零，net-contact横向也约为零；法向合力仍为已知1.02784 N。该已安装GPU PhysX/CPU张量管线的字段不能据此恢复真实切向牵引，不能把net-contact改称完整摩擦合力。只执行这一个语义夹具，没有给正式美工刀施加外力；失败的Vec3读取及修正后的Vec2报告都保留。证据 `runs/support-pressure-20261003/calibration/native-friction-field-v151-retry1/calibration.json`。
