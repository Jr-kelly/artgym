# G2＋Wuji 桌面取刀基线（持续更新）

续接入口：[G2_TABLETOP_HANDOFF.md](../G2_TABLETOP_HANDOFF.md)。独立分支 `feat/g2-wuji-tabletop-20260925`，本机工程 `/data/research/artgym-g2-tabletop-20260925`，实验目录 `runs/g2-tabletop-v1`。旧成功版本及训练 PID 88339 保留；本阶段没有训练新策略。

截至2026-09-25 21:33 CST：固定A63/B65/C66均已通过两轮、10mm基本到位和全程稳定。B/C从正常桌面开始连续109秒，B/C未全过2mm；C使用仿真定位和接管时物体真值，属于理想初始化对照。B/C获取轨迹2670帧完全相同，冻结推理与实际历史审计通过。20次小变化清单已预先声明，尚未完成；没有新训练，旧失败全部保留。

## 模型、控制及约束

- 源资产为用户目录 `/data/research/ArtBot/G2_crsB_wuji/robot.usd`，附属 USD 层与 config 同目录。导出 88 链接、87 关节；右臂 `idx61_arm_r_joint1` 至 `idx67_arm_r_joint7` 七自由度，加原 Wuji 右手 20 自由度。其余关节固定零位。没有沿用 Franka 参数。
- 末端父坐标 `arm_r_end_link`，Wuji 子坐标 `hand_r_base_link`，安装平移 `[0,0,0.0341]` m、旋转 `Rz(-90°)`。USD 的非平凡 child joint frame 按完整变换导出。逐项质量、惯量、限位、驱动、来源哈希见 [audit.json](../assets/robots/g2_wuji/audit.json)。腕部 FK 与实际仿真轨迹差约 1 μm / 2.4e-6 rad。
- G2 源驱动 100 Nm/rad、1 Nm·s/rad。有效 A 对照在此驱动下完成开合，但世界漂移 79.7 mm；当前右臂驱动改为 1000/20，保留源力矩及速度上限。后续增加关节误差积分 1/s，积分限幅 0.08 rad，只经有限力矩驱动写关节目标。此为仿真控制调试，未经真机标定。
- G2 缺失的碰撞体以逐链接视觉凸包补齐；按源配置禁用 G2 内部自碰撞，并排除臂手接缝；保留原 Wuji 手指碰撞过滤。机器人与刀、桌面碰撞开启。此模型不构成完整自碰撞规划验证。
- 原手/刀质量、摩擦、驱动与冻结模型保留。刀具 147×19×11 mm、35 g；刀身厚 8 mm、上方滑块厚 3 mm。滑块刚度为 0，无动作直接驱动滑块。原训练手部禁用重力的设置保留；G2 臂和刀具启用重力。
- 仿真为 Isaac Gym / PhysX，物理 120 Hz、控制 30 Hz。该运行库对 G2 actor 的 DOF 力传感器返回不支持；v12 起力矩数组为 NaN，不宣称实测扭矩。保留关节速度、实际角度、目标、物体位姿及逐手指接触配对。
- 首轮桌面高 0.75 m，刀具正常平放。后续 0.80 m 桌面为明确单列的G2可达性对照，旧条件保留。全部状态写入限于第一帧物理执行之前；抓取开始后只写电机目标。无刀具焊接、吸附、外力保持或缓存抓姿重置。

## 已完成对照及失败

以下均为开发案例，修改了抓法或控制参数，不能混合成冻结方案的泛化成功率。

| 实验 | 抓取/接管 | 伸缩结果 | 稳定性或失败 |
|---|---|---|---|
| A-g2-initialized-v4 | 预置 | 20 s 四端点均 <2 mm，行程 40.019 mm | 世界漂移 8.450 mm，通过 |
| A-g2-source-gains-v4 | 预置，源臂驱动 | 四端点均 <2 mm | 世界漂移 79.714 mm，不稳定 |
| A-g2-integral-v12 | 预置，新臂控制 | 四端点均 <2 mm，行程 40.090 mm | 世界漂移 7.744 mm / 0.150 rad，通过 |
| B-direct-grasp0-v5 | 未抬起 | 未操作 | 原功能抓姿手指穿桌约 40–44 mm |
| B-rolled-…-v7/v8 | 未抬起 | 未操作 | 抬高避桌则错过刀；下探仍未形成夹持 |
| B-edge-…-v9/v10 | 未抬起 | 未操作 | 接触主要在上表面，未形成有效侧夹 |
| B-normal-squeeze-grasp0-v12 | 抬升 20 cm，搬运掉落 | 未操作 | 4 mm 电机目标预压不足以保持搬运 |
| B-pinch8-transport-grasp0-v14 | 抬升、搬运、停稳成功 1/1 | 该诊断未请求操作 | 8 mm 电机目标预压，实际关节被接触阻挡 |
| B-pinch8-teacher-grasp0-v15 | 接管前抓取成功 1/1 | 条件开合 0/1，全段 0/1 | 相对原操作抓姿约 92° 差，接管后掉刀，0 完整循环 |
| B-normal-seat-grasp0-v13 | 抬升后直接插值就位 | 未操作 | 就位掉落 |
| B-contact-seat-grasp0-v16 | 抬升后 | 未操作 | 中途 IK 解分支跳跃，门禁中止，保存部分轨迹 |
| B-yaw90-contact-seat-grasp0-v17 | 抬升成功，就位掉落 | 未操作 | 连续 IK 可达，但自由刀身偏离预规划接触 |
| C-pinch8-student-ideal-grasp0-v21 | 接管前抓取成功 1/1 | 条件开合 0/1，全段 0/1 | 理想初始化；接管后掉刀，0 完整循环，行程 7.543 mm |

v1–v3 的早期 A 失败来自在 `prepare_sim` 前初始化的接口错误，均保留；不能以这些失败证明改物性的必要性。v4 将唯一 episode 初始化移至 prepare 后、首次 simulate 前，并恢复原环境首帧观测语义，A 恢复成功。

`plan_g2_edge_grasp.py` 的几何侧夹约束已从最近顶点改为相对侧面支持点。`plan_g2_seating.py` 求解保持接触的腕部＋手指目标；有界腕部平移调整使中间接触几何残差 <0.1 mm，但物理验证仍失败。v18–v22 的 oracle 位姿反馈依次暴露腕部限位、启动参考不连续及跟随自由刀身旋转导致的跟踪失稳；均保留，未作为成功结果。通过冗余关节7=-0.7 rad、桌面 x=0.45 m / yaw180 找到全路径至少 0.258 rad 限位余量；这仍是正常桌面内部摆放。v23 改接触法向、v24 延迟释放预压、v26 半侧滚换握、v29 先转到训练朝向、v30 分批小幅换握均失败。它们不支持“仅改其中一项就能解决”的解释。v31 逆静力开环仍掉落；v32 平移真值反馈引发持续下沉，位置偏离 63 mm 后中止；v33 手指反馈暴露支持点 Jacobian 漏项并中止，v34 已修正（中心差分误差 5.14e-11），但仍在早期遇到拇指接触不可达，说明导数修复不足以解决问题。v35 按真实抬升末态重建换握起点仍失败；后续结果见文末。所有失败保留。

首轮 A/B/C 基线都是固定单案例，无统计泛化结论。B 与 C 的前 600 帧抓取过程另做逐项一致性核对；两者接管后均失败只能缩小到末态/策略接管相关范围，不能据此认定唯一原因。

## 策略接管与数据来源

冻结 teacher SHA256：`4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac`。冻结 student 为既有 latent MSE final1000。使用先前公开权重，不重新训练。

所有位置/姿态按**实际测量腕部坐标**变换。初始参考在接管时固定；支持指动作围绕实际最后电机目标，拇指为逐步增量；RNN 仅在接管时清零。默认停稳 2 s，student 使用最后 50 帧实际关节角与零保持动作历史。操作阶段为外部时钟 20 s，每 5 s 换向，目标是原下限与下限＋40 mm，与仿真到位信号无关。

| Student 输入 | 本阶段来源 | 部署所需来源 |
|---|---|---|
| 当前/初始关节角 | 仿真关节读数 | 编码器 |
| 指尖位置 | 关节角＋相同 Wuji FK | 标定 FK |
| 上一步动作、50 帧历史 | 实际执行/停稳记录 | 实际执行记录 |
| 开/关目标 | 外部时钟 | 外部任务命令 |
| 固定几何尺寸 | 资产尺寸 | 实物尺寸 |
| 接管时刀身及滑块初始位姿 | 一次仿真真值 | 视觉/标记/其他独立估计，尚未实现 |
| 实时物体特权量 | 操作时不读取 | 不需要 |

因此 C 的初始化只能称“理想初始化对照”。如采用 v18 的就位控制，抓取阶段另含实时真值定位，也要单列；不能宣称可部署。接口审计 teacher 观测/动作误差约 1e-7；student 输入误差 1.19e-7、动作 2.32e-6；更改实时物体真值不改变 student 操作输入。

## 复现

在按本项目 README 安装的 Isaac Gym Python 3.8 环境运行。资产、功能抓姿已在此分支，G2 无需再次导出。若需重导出，执行 `python -m scripts.export_g2_tabletop --help`；读取 USD 的 Python 必须安装 usd-core。

先下载原权重（复用旧 Release，不重复上传）：

```bash
cd /data/research/artgym-g2-tabletop-20260925
mkdir -p weights/g2-frozen
gh release download wuji-experiments-20260923 --repo Jr-kelly/artgym \
  --pattern 'wuji-core-teacher-student-20260924-teacher.pth' \
  --pattern 'wuji-core-teacher-student-20260924-student.pth' --dir weights/g2-frozen
```

A，预置→teacher（每次使用新的 `--name`）：

```bash
python3 -m scripts.launch_g2_trial --name A-reproduce-001 -- \
  --group A --operation-yaw 90 --arm-gain-scale 10 --arm-damping-scale 20 \
  --arm-integral-gain 1 --video --camera hand \
  --teacher weights/g2-frozen/wuji-core-teacher-student-20260924-teacher.pth
```

B，已经完成的侧夹→teacher 失败基线，保留完整状态与视频：

```bash
python3 -m scripts.launch_g2_trial --name B-direct-takeover-001 -- \
  --group B --operation-yaw 90 --yaw 180 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan assets/robots/g2_wuji/plans/edge-pinch8.json --video --camera hand \
  --teacher weights/g2-frozen/wuji-core-teacher-student-20260924-teacher.pth
```

当前就位反馈对照（仍是实验，不能预告成功）：

```bash
python3 -m scripts.launch_g2_trial --name B-oracle-seating-001 -- \
  --group B --operation-yaw 90 --yaw 90 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan assets/robots/g2_wuji/plans/edge-pinch8.json \
  --seating-plan assets/robots/g2_wuji/plans/contact-seating.json \
  --seat-seconds 8 --seat-feedback object-truth --video --camera hand \
  --teacher weights/g2-frozen/wuji-core-teacher-student-20260924-teacher.pth
```

C 的命令是在上述侧夹 B 命令上改为 `--group C` 并增加 `--student weights/g2-frozen/wuji-core-teacher-student-20260924-student.pth`。已完成这一理想初始化失败基线；后续就位方案的 C 尚未运行。其他 Python 环境通过 launcher 的 `--python /path/to/python` 指定。

每次试验自动复制独立源码 pin、保存 SHA256、完整命令及日志。结果包括 `report.json`、`trace.npz`、`takeover.json`、`physics.json`、规划数据和无文字 `continuous.mp4`；中止试验保存 `failure.json` / `partial-trace.npz`。用 Isaac Gym 环境的 Python 执行 `-m scripts.audit_g2_trajectories` 汇总轨迹审计。

Release 增量证据包包含全部结束试验的轨迹、失败日志及去重的源码覆盖文件。历史源码可用 `python3 -m scripts.restore_g2_evidence --evidence /path/to/g2-wuji-tabletop-evidence --trial B-pinch8-teacher-grasp0-v15 --output /new/source/path` 从本仓库恢复，并核对每个文件的 SHA256。

指标分开记录：抬升、抓取到接管、抓取后的条件开合、全段；每个 5 s 端点末 0.3 s 的 10 mm 基本标准与 2 mm 诊断；刀身世界漂移 10 mm / 0.25 rad 稳定、手内相对漂移及掉落。漂移参考仅在接管时固定。没有抓取成功时，条件伸缩为 N/A。首次固定方案真正接通后再冻结、预注册约 20 个位置/朝向变化，保留全部失败。

## 后续有限诊断（v23–v34）

v25 半侧滚取刀虽能握持搬运，但关节插值出现较大绕行，未作为冻结方案。v27 大幅逐指换握几何残差约20mm，未进入仿真。v29预先把已持刀移到训练物体朝向后仍换握掉落；A平躺刀具重力诊断握持稳定但回收误差16.14mm，不能把重力认定为唯一根因。

v31规划接触力满足重力及合力矩平衡，再用原Kp与J转成关节目标；接触力仅为计算变量，无直接施力。v33/v34在此基础上用实际物体位姿修正指尖接触，属于理想定位控制。全程原手刀物性、冻结策略不变。v32/v33的界限中止保留部分轨迹与从桌面开始的视频。

新握持判据检查最后一秒实际停稳、刀身离桌、手内漂移和拇指/至少两支持指接触；功能姿态差单列。对原B/C回查仍为抓取1/1、条件操作0/1、全段0/1，无泛化成功率结论。

逆静力诊断复现（已知失败，不是完整方案）：

```bash
python -m scripts.plan_g2_static_seating \
  --input assets/robots/g2_wuji/plans/contact-seating-radial.json \
  --output /tmp/seating-static.json
python3 -m scripts.launch_g2_trial --name B-static-reproduce-001 -- \
  --group B --operation-yaw 90 --yaw 180 --dx -.05 --wrist-posture -.7 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan assets/robots/g2_wuji/plans/edge-pinch8.json \
  --seat-seconds 12 --seating-plan /tmp/seating-static.json --video --camera hand
```

更详细逐次参数与完整命令以各试验 `-process.json` 和源码恢复清单为准。下一步仍是解决换握接触过渡；尚无证据需要重训整套teacher。

## 桌面端面支撑换握（v39，在途）

v35按实际持刀重建几何起点仍掉落。v36–v38先后验证接触反馈、完整刀身姿态伺服和只增加纠偏的残差控制，均未成功；不能再把失败只归于起始参考或数值IK精度。

v39尝试由机械臂把已从平放桌面抓起的刀转为竖直、降到同一桌面，使模型平端支撑刀重，再换握并重新抬升。初始仍是正常平放、没有夹具或桌边；此路线依赖现有简化刀具的平端面，实物端部形状尚未验证。手网格几何净空14–17mm，G2连续IK可达但途经腕关节限位。是否形成端面支撑、是否碰桌、是否真实换握成功必须以物理轨迹为准。当前尚无成功结论。

```bash
python -m scripts.derive_g2_held_grasp \
  --trial runs/g2-tabletop-v1/B-static-seat-grasp0-v31 \
  --output /tmp/actual-held-grasp.json
python -m scripts.plan_g2_seating --grasp-plan /tmp/actual-held-grasp.json \
  --normal-path radial --squeeze-schedule hold --output /tmp/measured-seating.json
python3 -m scripts.launch_g2_trial --name B-table-support-reproduce-001 -- \
  --group B --operation-yaw 90 --yaw 180 --dx -.05 --wrist-posture -.7 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan assets/robots/g2_wuji/plans/edge-pinch8.json \
  --seat-seconds 12 --seating-plan /tmp/measured-seating.json \
  --table-supported-seat --upright-yaw 250 --video --camera hand
```

上面的`B-static-seat-grasp0-v31`实测规划输入可从增量证据包的trials目录恢复，或者先运行已记录的v31复现命令。它只为规划提供实测数据，绝不用于仿真状态重置。

## 后续接管与支撑诊断（v40–v47）

v41松手时刀身已倾斜3.53°，逐步失稳并倒下；v43因不必要的长轴yaw恢复导致腕部25mm预检中止，未实际执行找正。v46改为仅纠正倾斜并从实测状态卸压/开手，在途。A打开滑块初态虽能握住，却不能完成回收（42.09mm末端误差），证明不能把竖刀中被动伸出计为学习策略成功。

原抓姿1 A-v45成功一轮、端点2mm通过；偏移4mm的A-v44失败。因此另一端着桌路线保留原抓姿1，通过刀轴朝上让重力保持闭刀。原手网格最小净空0.885mm，实际手/桌接触必须检查，未用新物性消除碰撞。

负端着桌的两个机械臂端态在75cm桌面不能同时满足当前IK；显式80cm桌面对照可达。80cm初始接近、抓取、抬升及转竖/下降路径完成几何预检，位置残差<1.7微米；A-v47先做20s复测，B尚未启动。此为明确新增桌高条件，保留75cm全部轨迹；不把场景变化藏在成功率中。


## 19:44 CST 闭刀竖起成功，转腕失稳定位（v48–v53）

A-grasp1-table80-v47完成20s两轮：四端点2mm通过、40.019mm行程、6.30mm/0.215rad漂移稳定。负端着桌仍明确为80cm桌面单列条件，未更改手刀物性。原A/B/C固定基线结果保持不变，尚无B/C完整成功。

v46未真正执行找正，原因是旧SciPy单向量align_vectors产生非最短旋转（意图0.0615rad却返回0.2985rad），导致37.5mm腕位移预检中止。已实现并验证minimal_alignment，实际校正7.13mm，在25mm边界内；parallel/antiparallel及实测姿态审计见minimal-tilt-audit-v49.json。不能将此记为物理找正失败，修正后的正端着桌尚未重跑。

v48负端着桌合并倾转/yaw中掉落；修复支撑判据，不能只因掉在桌上仍有接触就认为端面支撑成立，现需倾斜<0.15rad、刀中心高于桌面60mm以及最后1秒接触≥80%。v49重求12mm预压同时轻微改变几何，故不是纯压力对照；新增retarget_g2_pinch_pressure.py仅改变闭合目标，严格保持wrist/touch/open后，v50仍转竖失败。v51先yaw后倾转的CPU路径预检失败（120mm/0.433rad），因shell未短路误启动，已立即中止，标PreflightAbort，不作为物理结论。

v52改为先倾转到竖直、再yaw，保持原8mm侧夹。已成功倾转且五指接触、滑块闭合；随后yaw到75°时约20s失去接触并掉落，全部部分轨迹和视频保留。关节命令最高速度未超G2限速，但yaw有较快关节变化和跟踪误差，尚不能据此认定唯一根因。

B-negative-slow-yaw-grasp1-v53（PID3742855）只将最后yaw从5s延长15s，其他几何/物性/控制不变，用于区分速度/跟踪因素。未训练新模型、未做20扰动验收。原88339仍运行，最近只读GPU负载34%。v39之后尚未进入Release，下一份增量包合并排除v1+v2已发布清单，避免重复上传。


## 19:50 CST 慢速yaw通过，补齐全臂桌碰撞门禁

v53与v52前540帧相同，15s转腕保住五指接触和闭刀，转腕末刀轴倾斜0.0136rad。随后下降并非再次掉刀：G2腕部/前臂先碰桌，刀中心停在0.963m、刀端距80cm桌约90mm，端面接触0%。原先只查手指桌碰撞不足以说明G2整条路径可执行；原始物理已有robot_table_contacts，已据此定位并保留此失败。测得驱动误差最大约0.47rad，不应继续下压。

新增g2_table_collision.py按导出碰撞凸包、完整G2 FK与实际桌盒做分离轴检测（面法向和棱边叉积），在机械臂/手掌路径加入2mm规划余量；实际任何臂/掌桌接触立即中止并保存轨迹。v53最终命令几何穿桌：arm_r_link5/6/7及手掌，最大约51mm。负端着桌原功能抓姿1本身还存在G2腕link7约3mm实质穿桌（2mm余量后5.1mm），因此不再仅凭手指净空0.885mm宣称该路线可用。

几何考虑向刀上端平移60mm侧夹，可清除取刀腕部碰桌，但index超出刀端、需实际验证另四指，且原功能抓姿的腕碰桌仍在；仅保存edge-pinch8-upper60-v54.json候选，不启动物理。9个不转yaw的桌面位置端态均未通过G2 IK，见negative-no-yaw-endpoint-search-v53.json；不将预检不通过计为物理试验。

回到正端着桌：原三个功能抓姿的G2全臂/掌几何均通过桌碰撞预检。B-positive-corrected-level-grasp0-v54（PID3777023）只重测已修复minimal_alignment的找正/卸压/重抓路线，75cm桌、原8mm侧夹；此次only-grasp明确不调用策略。该方向会被动打开滑块，不能计作策略伸出，若重抓通过仍需经正常腕部重力姿态使其被动回闭再验证接管，不直接驱动滑块。

评分修正：操作中真实掉落或刀桌接触使whole_success为False，不能仅以手内相对位姿小而通过；循环只否决发生掉落/碰桌的那一轮，保留此前完整轮数。原A47重算仍通过两轮，合成注入最后帧桌接触的纯评分诊断得到整段失败/1轮，见operation-drop-score-audit-v54.json；未改物理轨迹或旧报告。


## 19:54 CST 正端找正后的释放判据对照（v54–v55）

v54实际找正执行完四次，刀桌支撑100%、臂/掌/手指无桌碰撞；倾斜从0.0615rad降至0.0489rad，但未达到原0.02rad控制放行阈值，故中止在释放之前。不能说已松手成功，也不是再次掉刀。实际最后夹持拇指/index/ring/pinky有接触。

按当前35g两刚体的实际位姿计算重心投影，v54在建模19×8mm端面内的最小余量0.908mm；v41找正前只有0.466mm，原v41松手后投影越界并倒下。新增显式standing-level-gate=support-projection对照，要求实际刀桌接触≥80%、总倾斜<0.15rad、两刚体重心沿重力投影距离端面边界≥0.5mm。这是释放前的几何候选筛查，不能代替实际无手支撑的稳定性。保留默认tilt门禁及v54失败，不改变控制幅度或任务操作判据。

B-positive-com-release-grasp0-v55（PID3792954）只改变上述放行判据，接着执行实测卸压/开手/撤离/功能重抓。仍only-grasp，不调用策略；滑块被动打开问题尚未解决。当前分支已推100b1fa，v55新增判据代码未推。下一次增量Release拟收v39之后的结束试验和代表视频，排除前两包，不重复历史权重。

## 当前正端支撑重抓对照的复现命令

这是尚未接通冻结策略的抓取诊断，`--only-grasp` 不运行 teacher；正端支撑阶段会被动打开滑块，不能算学习策略的伸出。保持首轮75cm正常桌面，无夹具或桌边条件。

```bash
# 在项目 Isaac Gym Python 环境中生成开指规划（只生成电机目标）
python -m scripts.plan_g2_functional_open --grasp 0 --end positive \
  --gap .012 --output /tmp/g2-functional-open.json
python3 -m scripts.launch_g2_trial --name B-positive-release-reproduce-001 -- \
  --group B --operation-yaw 90 --yaw 180 --dx -.05 --wrist-posture -.7 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan assets/robots/g2_wuji/plans/edge-pinch8.json \
  --table-supported-seat --upright-yaw 250 \
  --table-regrasp-plan /tmp/g2-functional-open.json \
  --level-standing-knife --standing-level-gate support-projection \
  --measured-release --only-grasp --video --camera hand \
  --teacher weights/g2-frozen/wuji-core-teacher-student-20260924-teacher.pth
```

精确历史复现优先恢复指定试验的源码与输入 pin；几何规划器后续版本可能产生不同浮点轨迹，不能冒充旧试验逐帧重放。新增整臂/掌桌面预检采用当前导出碰撞凸包与2mm规划余量，实际接触则以物理引擎为准，出现臂/掌碰桌会中止并保留部分轨迹/视频。此检查不等于G2完整自碰撞验证。


## 20:02 CST 正端释放通过，功能闭合没有建立对夹（v55）

v55完成真实平放取刀→正端放回桌面→找正→卸压/释放→撤离。松手后全部五指无接触，刀具在桌面独立保持竖立（中心0.823500m）；功能开手接近时腕位姿约1.1mm/0.00084rad误差，没有机器人桌碰撞。但闭合阶段拇指接触0帧，index仅15帧、ring7帧、其他很少；重新抬手后刀留在桌上，故整个抓取/接管失败、未调用策略。不是完整成功，也不是刀具从桌面掉落。

原闭刀功能抓姿拇指接触在刀具局部y≈6.89mm、z≈−6.91mm，接近闭合滑块端部；此时滑块已被动全开，该处只剩y=4mm的刀身表面。因此缺少拇指对夹与本次实测相符，但不排除其他控制因素。

下一步有界地比较抓取阶段的身体夹持目标：让拇指接触刀身外角，避开滑块通道，四指从背面闭合，只改变电机目标，不改物性/策略。positive角的首次CPU几何IK失败27mm，不启动物理；negative角正在CPU预检。新增plan_g2_body_regrasp.py保存几何门禁结果。新runner允许读取明确的close_q/touch_q，并在relift末检查真实抬升及对夹；失败即中止，避免继续空手搬运。

被动回闭后备阶段已实现为可选gravity-close-before-takeover，先在空中用G2电机把刀轴转向上，静置3s，再恢复原功能目标和操作姿态；几何预检可达/无桌碰撞，但尚未在物理中执行。滑块始终刚度0且无外力，回闭要求2mm误差，不能算冻结策略操作成功。当前还没有任何新完整B/C成功，未训练、未20扰动。


## 20:05 CST 刀身外角闭合候选进入物理（v56）

negative外角touch/close几何可达；12mm开口的拇指IK误差1.923mm未通过1mm预检，改为显式8mm开口后误差<10μm、全过程手指桌面几何净空14.19mm。另有刀身正面候选几何通过，但可能阻挡滑块回闭，暂未物理运行；positive外角不可达保留失败。

B-body-corner-reclosure-teacher-v56（PID3852334）保留v55成功的取刀/放端/释放段，在功能接近时用negative外角拇指+四背面指，先到触碰目标再2mm电机目标过行程闭合。若重新抬刀通过才继续搬运、19+2秒有界被动回闭/恢复动作及冻结teacher20s。实际运行结果待收，任何阶段失败均不能算完整成功。新阶段仅用G2/手指电机目标，滑块不驱动；物性/权重仍原样。

本轮准备增量Release v3收v39–v55已结束17项及代表性完整无字视频，v56在途单列，不覆盖前两版。


## 20:08 CST 第三份增量Release已核验

https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-tabletop-support-20260925-v3 已发布并逐项校验6附件大小/SHA256。新增17项结束试验，15.2MB证据包，排除前两份54项；v55源码恢复3866文件通过。三个完整无字视频为A47预置成功、v53下降碰桌失败、v55独立立刀但功能重抓失败。快照v56仍在途，未纳入结束试验。代码已推0a38ba0；新阶段仍不代表完整B/C成功。


## 20:12 CST 外角夹持未能抬刀，正面对夹对照

v56外角夹持建立五指接触，但relift中刀只升约0.8mm便失去接触，刀回到竖立桌面；无手桌碰撞。新relift门禁正确中止，未执行被动回闭或teacher。接触法向不对称仍可能影响稳定性，不能只据此说压力不足。

v57只把thumb改到刀身正面，与四指背面对夹；相同8mm开口/2mm电机目标过行程、原腕部功能关系，新增几何误差<10微米、桌面净空14.19mm。该诊断only-grasp，不运行策略；正面拇指可能阻挡被动回闭，先查抓持是否建立，再决定有界的倾斜承托/松拇指对照。v57已启动，PID见B-body-face-regrasp-only-v57-process.json。


## 20:15 CST 后备被动回闭方案的几何预检

v57正面对夹仍在运行，尚未验证抬升。为了避免正面拇指挡住滑块，新增可选gravity-close-support=tray：让刀轴向上30°，重力分量同时把刀背压向四个支撑指，短暂开拇指后靠重力回闭，再恢复原功能目标。全程只有机器人电机动作，无滑块驱动；此阶段尚未物理执行，不计成功。

目标重力knife-local为[0,−8.496,−4.905]m/s²。原最短转腕路径末端触及G2限位；有限比较world yaw −30/−15/+15/+30后，+30方案全程位置残差<0.22微米、最小关节余量0.208rad、无臂/掌桌碰撞。world yaw保持刀内重力方向不变，仅改善G2可达性。预检文件passive-tray-yaw-preflight-v57.json；若v57实际抓持成立，再按此方案做物理对照，不直接扩大训练。


## 20:18 CST 连续功能重抓与搬运首次通过（v57）

B-body-face-regrasp-only-v57完成真实平放取刀→端面支撑→完全松手→功能腕姿正面对夹→重新抬升20cm→搬运→停稳。最后1秒全部帧thumb+≥2支撑指接触，刀桌无接触，相对漂移3.96微米/0.000125rad；抓取到接管位置通过1/1。相对原功能抓姿6.06mm/0.0670rad误差单列，不能用稳定性掩盖。滑块仍约0.0164m（接近全开）；此次only-grasp，操作未请求，整段成功尚未评估，不能写成0/1或完整成功。

B-face-tray-reclosure-teacher-v58（PID3914214）保留相同抓取段，新增经过G2几何预检的30°倾斜承托、world yaw+30°、仅拇指暂开以允许重力被动回闭。随后用有限驱动在2秒内平滑回到原功能电机目标，再8秒回操作姿态，停稳积累真实历史。恢复的是电机目标，不是写入缓存关节/物体状态。若回闭/握持通过，接冻结teacher外部时钟20秒；任何失败保留且不计学习操作成功。原手刀物性及权重不变。

最新发布仍为v3（到v55）；v56失败和v57抓持成功尚未上传，待下一增量。没有C新成功、未20扰动、未训练。

## 已通过的功能重抓诊断与后续回闭对照

v57完成连续取刀、立刀、释放、正面重抓、再次抬升和搬运停稳，抓取成功1/1。该阶段滑块仍开着，`--only-grasp`明确不评估操作。

```bash
python -m scripts.plan_g2_body_regrasp --thumb-corner face --gap .008 \
  --squeeze .002 --grasp 0 --output /tmp/g2-body-face.json
python3 -m scripts.launch_g2_trial --name B-body-regrasp-reproduce-001 -- \
  --group B --operation-yaw 90 --yaw 180 --dx -.05 --wrist-posture -.7 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan assets/robots/g2_wuji/plans/edge-pinch8.json \
  --table-supported-seat --upright-yaw 250 \
  --table-regrasp-plan /tmp/g2-body-face.json \
  --level-standing-knife --standing-level-gate support-projection \
  --measured-release --only-grasp --video --camera hand \
  --teacher weights/g2-frozen/wuji-core-teacher-student-20260924-teacher.pth
```

v58在上述命令中去掉`--only-grasp`，增加`--gravity-close-before-takeover --gravity-close-support tray --gravity-close-yaw 30`。该回闭/teacher流程正在物理验证，尚未作为成功方案。承托阶段只打开拇指电机目标、四指维持支撑，滑块仍完全被动；返回原功能电机目标也是有限驱动的真实过程，不写入缓存物理状态。


## 20:23 CST 当前代码A回归通过

A-current-guards-headless-v58完成20秒2轮：四端点<2mm、行程40.0897mm、固定参考世界漂移7.7445mm/0.1498rad，无掉落且稳定。与A-g2-integral-v12逐帧q/arm_q/object/wrist/slider/targets/action完全一致（a-v12-v58-physics-parity.json）；新增碰撞门禁/回闭可选代码未改变原A行为。A已结束，v58实际桌面流程继续。最新远端.106/.93:30147均Connection refused，未更改远端或原训练88339。


## 20:27 CST v58被动回闭与返回通过，teacher待收

v58实际承托阶段回闭到slider下限，hold检查误差3.73e-9m；期间拇指接触为0、四支撑指接触保留。原功能电机目标通过2s真实驱动恢复后五指接触，返回操作姿态时slider仍在闭端约0.03mm内、刀身保持。当前已进入settle_history，将以固定接管参考/冷RNN/实际50帧历史开始冻结teacher。尚未收齐20s操作，不能提前宣称B成功。


## 20:31 CST 连续B58已接teacher但回收差1–2mm未过线

v58完成从桌面开始105秒连续物理：抓取/真实重抓/承托被动回闭/返回均成功，冻结teacher操作20秒、行程37.994mm、无掉落，固定参考漂移3.558mm/0.1526rad稳定。两次伸出误差1.922/2.016mm；两次回收末段最大误差10.946/12.332mm，最终误差约10.83/10.84mm，超过预定10mm标准，故0完整合格循环、条件操作0/1、全段0/1，不能放宽阈值报成功。

A/B末端审计a-b-retraction-endpoint-audit-v58.json：B手内刀沿初始刀轴偏移约5.61mm，旋转0.125rad；原A刀轴重力分量−0.481m/s²（帮助回收），B实际+0.488m/s²（帮助伸出）。B回收末段thumb仍输出动作，多数关节未达限位，不能直接归为硬关节限位。存在重力方向反转，仍不认定唯一根因。

有界操作姿态对照：固定腕部位置，将名义刀轴上倾10°，其余手刀参数/模型/目标/5秒时钟不变；改变的是G2目标姿态，不是驱动物体或滑块。IK残差<14nm/8.3e-8rad。A-operation-up10-v59先验证新姿态A，PID见process.json；A通过后再发同一B流程。新矩阵operation-knife-up10-v59.json及设计说明保存。B/C仍未完整通过，未20扰动或新训练。


## 20:34 CST 上倾10度A通过，B姿态对照启动

A-operation-up10-v59通过20秒两轮、四端点2mm内，世界漂移6.519mm/0.1557rad稳定。B初始接近/抓取/抬升IK与原v58最大差4.6e-9rad，见operation-up10-acquisition-ik-parity-v59.json，非换初始抓法。B-up10-tray-teacher-v60已启动，PID见process.json，除最终操作姿态上倾10度（同时影响前往该姿态/承托往返路径）外保持v58条件。待判断是否修复回收不足；不改10mm阈值，不根据单项对照认定唯一原因。


## 20:38 CST 第四份增量Release已核验

https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-tabletop-handoff-20260925-v4 已发布，5附件大小和SHA256均通过；新增5项结束试验，排除前三包71项，证据9.7MB。完整62秒功能重抓诊断及105秒取刀→teacher回收未达标视频已按结果命名，均无文字。B58源码恢复3867文件一致。分支5e29c7a。B60仍在运行，不计为成功或结束试验。


## 20:43 CST B60仅搬运IK失败；补做从实际末态出发的整路径筛查

B-up10-tray-teacher-v60已真实重抓并重新抬起，但其负号肘部IK分支在直达上倾10°操作位时触及关节限位，残差2.32mm/0.0114rad，门禁在第1650帧中止。没有执行新姿态teacher，不能认为上倾重力对照无效。之前从A静态IK分支出发的局部路径可达并不适用于B实际分支；已分别记录actual-B-operation-to-up10-v61.json和fixed-wrist-posture尝试，均未放宽门禁。

从B60实际抬升末态的电机参考出发，有限比较4个world yaw与6个±20mm位置候选；全路径保留table凸包碰撞和IK门禁。yaw+15与+30均可达，进一步沿B58实测手刀关系核验承托和返回路径也通过。选+15为较小转动，即操作yaw105、保留刀轴上倾10°；world-z旋转在代数上完全保持手内重力方向，便于区分可达性与重力效果。路径部分经过源关节限位，不能称有充足裕量，仍需物理验证。

A-up10-yaw105-v61先验证该最终操作位，PID见process.json；A通过才发B。矩阵operation-up10-yaw105-v61.json和up10-continuous-pose-candidates-v61.json/up10-yaw-tray-roundtrip-v61.json保存。最新完整B结论仍是v58稳定但回收略超10mm，无C新成功或20扰动。


## 20:46 CST 最终候选操作位A通过，B62开始

A-up10-yaw105-v61完成20秒2轮，四端点2mm均过、漂移6.398mm稳定。B-up10-yaw105-teacher-v62已启动，PID见process.json；从实际抬升末态出发的搬运、承托和返回IK已预检通过。此B结果未知，不把A等价当B成功。若B62端点/握持/稳定通过，下一项是相同参数、同一物理抓取段的C学生理想初始化；尚未冻结20扰动方案。


## 20:56 CST 新操作位失败与保留抓取路径的后续对照

v62从正常桌面到接管仍抓取成功1/1，但冻结teacher操作后刀身大幅翻转（2.056rad）、世界漂移42.26mm，四端点10.659/29.382/11.036/28.809mm均不合格；未触桌或检测到真正掉落，归类operation_pose_escape，不能把“仍有接触”当稳定。完整105秒视频、轨迹保留。接管关系相对原功能抓姿8.535mm/0.219rad，较v58的6.016mm/0.125rad更偏，改变搬运/承托路径同时改变了末态，不能单独归因重力。

新增可选post-acquisition-pose：保持v58成功获取/承托/回闭/返回路径完全相同，仅在其后用4秒真实G2电机调整腕姿，再停稳、接管。限制额外位移≤20mm/旋转≤15度，手指电机目标保持，零物体状态写入。当前选择上倾5度、原yaw90；从v58真实返回末态电机参考预检，全路径IK位置<12nm/转角<6e-8rad且无臂掌桌碰撞（post-acquisition-up5-preflight-v63.json）。部分源关节边界仍很近，非大裕量方案。A-operation-up5-v63正在先验新腕姿；通过后再发相同旧抓取路径+B后置调整，不改10mm标准。

新增audit_g2_handoff_replay.py从50帧真实执行历史重建冻结策略、仅清零一次RNN，逐帧核对观测/动作/目标及固定参考；B58全部600帧三项误差均0（frozen-replay-B58-v63.json）。轨迹审核FK最大1.06微米/2.81e-6rad，关节命令与实测速度均不越源限速，角度浮点超限2.55e-7rad。该离线回放只证明接口执行一致，不增加物理成功样本。


## 20:59 CST A63通过，原获取路径后置调整进入物理

A-operation-up5-v63在上倾5°/yaw90下20秒两轮、四端点<2mm、世界漂移7.113mm/.1564rad稳定。B-original-path-post-up5-teacher-v64已启动（PID见process.json），仍正常75cm桌面、原B58所有获取/被动回闭参数；新增4秒G2腕部上倾5°在回闭返回之后，停稳历史之前，连续物理无重置。结果未知。

已将功能正面对夹及两个诊断操作位JSON加入Git可复现资产目录。新增小变化执行工具run_g2_small_variations.py，但未生成/执行验证样本；它要求固定A/B/C全段稳定通过后才能声明10个共享摆放×B/C共20次任务，范围x/y±5mm、yaw±2°，固定seed2026092501，每次来源于校验过的冻结源码pin。声明与状态分开、规划失败也保留计入整段分母，不调参重抽样。用当前失败B/C实测门禁拒绝，未误发任何验证。仍没有新训练。


## 21:04 CST 机械臂自身几何补查

新增audit_g2_self_clearance.py：按实际G2右臂关节轨迹、导出碰撞凸包及完整零位固定机构做SAT检查，包含面法向与边叉积；只排除两条关节边以内的连接壳体/安装接缝，以及另行处理的右手指自接触。B58每秒取样、末帧共106帧，414个候选链对均未检出>0.1mm凸包重叠。记录self-clearance-B58-stride30-v64.json；这只是采样诊断，非连续全路径认证，也没有更改源资产关闭自碰撞的物理设置。初版一次性投影阵列占8GB，已只中断该离线审核并改为256轴分块/先测面分离，完成相同SAT判据；原训练及B64均未受中断。

B58/B62接管电机目标逐项相同，实际受力关节角/接触关系不同；B62操作0.20s首次拇指失联、0.233s旋转超过0.25rad、1.733s漂移超过10mm（B58均未发生）。记录B58-B62-loaded-handoff-comparison-v64.json，只作为末态/接触敏感性证据，不认定唯一原因。


## 21:12 CST 后置5度仍未通过窗口，轴向3mm获取对照

B64从桌面起共109秒，抓取1/1、条件操作0/1、全段0/1。四端点末0.3秒最大误差为2.122/10.342/2.225/12.251mm；两次收回最后一帧虽为9.782/8.835mm，但不能替换预定窗口判据。无掉落、世界漂移3.898mm/.1383rad稳定，仍0完整合格循环。不能按某一早期日志帧进入10mm便计成功。

B58与B64前2490帧直至gravity_close_return的q、arm_q、物体/滑块/腕位姿、目标、接触计数全部逐项相同（B58-B64-acquisition-prefix-parity-v65.json）。B64冻结策略离线重放600帧观测/动作/目标误差均0。后置5°未导致B62那种翻转，但不足以通过回收窗口。

新增plan_g2_body_regrasp --wrist-axis-offset .003：仅把功能重抓腕相对刀轴沿+z移动3mm，尝试部分抵消接管时约6mm位置偏差；不修改前段侧夹、手指电机目标、物性、权重、20秒时钟。重算四组手指目标float32与原计划完全相同，几何手桌净空11.187mm，实际withdraw末态起的功能接近/重抓/再次抬升/搬运IK位置<0.4微米、转角<2.55e-6rad且无臂掌桌碰撞。后续自由物体/承托仍需实际验证，不能据预检宣布末态已改善。

B-axis3-post-up5-teacher-v65已开始（PID见process.json），保留B64后置5°及其余设置。完整B/C仍未通过、未声明或执行20变化、无新训练。下一步收v65实际末态与全程评分；若通过才发同条件C并标记理想初始化。

复现该有界诊断（使用新的name，按前文下载既有冻结权重）：

```bash
python -m scripts.plan_g2_body_regrasp --thumb-corner face --gap .008 \
  --squeeze .002 --grasp 0 --wrist-axis-offset .003 --output /tmp/g2-body-axis3.json
python3 -m scripts.launch_g2_trial --name B-axis3-reproduce-001 -- \
  --group B --operation-yaw 90 --yaw 180 --dx -.05 --wrist-posture -.7 \
  --arm-gain-scale 10 --arm-damping-scale 20 --arm-integral-gain 1 \
  --grasp-plan assets/robots/g2_wuji/plans/edge-pinch8.json \
  --table-supported-seat --upright-yaw 250 --table-regrasp-plan /tmp/g2-body-axis3.json \
  --level-standing-knife --standing-level-gate support-projection --measured-release \
  --gravity-close-before-takeover --gravity-close-support tray --gravity-close-yaw 30 \
  --post-acquisition-pose assets/robots/g2_wuji/plans/operation-knife-up5-v63.json \
  --video --camera hand \
  --teacher weights/g2-frozen/wuji-core-teacher-student-20260924-teacher.pth
```


## 21:15 CST 第五份增量Release已核验

https://github.com/Jr-kelly/artgym/releases/tag/g2-wuji-tabletop-operation-20260925-v5 已发布，5附件大小和GitHub SHA256逐项一致。新增5项结束试验（B60/A61/B62/A63/B64），证据11.6MB，排除前四包；B64源码/输入恢复3872文件核验通过。无文字视频分别保留105秒翻转失败与109秒收刀窗口失败。代码已推da4d69d；B65快照时仍在途，未列作结束/成功。B64额外110帧/414链对自身凸包采样也未检出重叠，仍不是连续认证。


## 21:22–21:25 CST 固定B首次完整通过，冻结C开始

B-axis3-post-up5-teacher-v65从正常桌面连续109秒（获取89秒+冻结teacher20秒），抓取1/1、抓取后的操作1/1、全段1/1；外部时钟两轮开合，四端点末0.3秒最大误差1.895/7.038/2.038/7.647mm，全部10mm内，无掉落且固定参考世界漂移4.114mm/.1592rad稳定。2mm严格诊断未全部通过。此次为调试中选出的单案例，不能作为泛化成功率。相对原功能抓姿位置差由B64的5.948mm降到3.624mm，旋转0.1285rad；这是改善接管几何后得到的结果，不认定唯一原因。

B64/B65前1080帧直至withdraw完全一致（B64-B65-acquisition-prefix-parity-v66.json）。B65冻结回放600帧观测/动作/电机目标误差0；实际腕FK约1.06微米/2.79e-6rad，命令与实际速度无超源限速。110帧自身凸包采样未检出重叠。

机器人/桌面并非全程零接触：approach有8帧、close有46帧拇指/小指碰桌，碰撞网格在桌面范围内最低0.211mm穿入，源PhysX contact_offset=2mm；没有臂/掌碰桌，抬起及操作阶段没有桌面支撑。这些如实记录在B65-finger-table-contact-clearance-v66.json，不能写成“手指从不碰桌”。仅是仿真接触与网格估计，不能当硬件触觉力标定。

C-axis3-post-up5-student-ideal-v66已在21:22:23 CST启动（PID7325，PID计数回绕后的小编号正常；原训练88339仍活跃）。launcher直接复制B65校验过的源码pin，两者SOURCE_SHA256清单哈希完全相同4b63cd7459d02e73f4d9788ebce5a3d6507fab3f394ce38863a5d73a425dba49，参数仅group B→C。Student冻结权重保持；实际50帧停稳历史、RNN只清零一次、接管初始物体真值明确理想初始化。结果待收，不提前宣布C成功。

若C同样通过，先做实际前2670帧一致性与冻结回放/实时真值不变性审计，再声明10个位置×B/C共20次的既定小变化。使用A-operation-up5-v63 / B-axis3-post-up5-teacher-v65 / C-axis3-post-up5-student-ideal-v66。当前没有声明或抽取验证样本；还没有新训练。B65完整无文字视频已保存continuous.mp4，待和C一起增量发布v6，不覆盖v5失败证据。


## 21:33 CST 固定A/B/C收齐通过；20次小变化已预先声明

C-axis3-post-up5-student-ideal-v66完成109秒连续桌面流程：抓取1/1、条件操作1/1、全段1/1，两轮10mm基本到位且稳定；四端点4.914/5.413/6.656/4.827mm，行程37.082mm，固定参考漂移5.185mm/.2355rad，无掉落。2mm诊断未通过。这是仿真定位与物体初始真值条件下的单案例，不是可部署或泛化验证。A63同一最终5°腕姿通过2mm及稳定；B65通过10mm及稳定。汇总abc-current-continuous-v67-final.json，旧pending快照保留。

B65/C66前2670帧直至接管完全相同，实际物性physics.json也字节相同；C冻结重放600帧的观测/动作/电机目标及实时物体真值扰动不变性误差均0。实际50帧历史均为settle_history，动作0；RNN接管时清零一次，初始目标/观测固定。依据B65-C66-acquisition-prefix-parity-v67.json、frozen-replay-C66-v67.json。

run_g2_small_variations.py已在固定ABC通过后声明10组共享摆放×两策略，共20次；x/y±5mm、yaw±2°，seed2026092501。文件runs/g2-tabletop-v1/g2-small-placement-v1.json及公开副本research/g2-small-placement-validation-v1.json，SHA256 20f313a7f96681241a71a6d83b8f9a8db057947f888dbaa9caa7b718a8c5b7a1。将先提交/推送声明，再启动；不修改该清单或失败样本，不在本组上调参。每次复制C66经哈希校验的冻结源码pin，保留全部日志、原始轨迹和视频；初始规划失败也保留在整段分母。当前只是已声明，尚未完成验证。

复现并继续已声明验证：

```bash
python3 -m scripts.run_g2_small_variations run \
  --manifest runs/g2-tabletop-v1/g2-small-placement-v1.json --concurrency 2
```

状态/分组结果写g2-small-placement-v1-results.json；不要并发启动多个driver。遇中断先核对driver和子进程，单个driver可恢复未启动项，已失败项不重跑。A/B/C权重及控制无新训练。新成功视频待增量Release v6，v5失败证据保留。


## 21:35 CST 验证driver已启动，冻结方案保持

预声明清单已先提交并推送GitHub 86b191b，随后21:34:47 CST启动唯一driver PID67920，记录g2-small-placement-v1-driver.json；初始B/C子进程为g2-small-placement-v1-00-B/C，2路并行，源C66冻结pin，原训练88339保持、整机GPU约99%。清单及public副本SHA不变，不能改样本或调参；driver/launcher源码SHA也写入driver记录，不要在途中修改或启动第二个driver。

结果进度读g2-small-placement-v1-results.json，完整日志在各试验同名.log；先核实实际PID，不能据旧文档重启。首批尚未结束，不当作20次成功。新简版可复现报告research/g2-tabletop-fixed-baseline.md给出A/B/C数字、普通桌面端立路线、所有student输入来源及原始文件位置；完整开发史仍保留。
