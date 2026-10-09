# G2＋Wuji 后段首次现场操作指南（v6，公开脱敏版）

本文件是完整操作指南的公开版，仅替换内部站点、示例网络地址、路径和容器名；真实现场版本及私有适配与依赖位于 [私有交付仓库](https://github.com/Jr-kelly/artgym-wuji-private-delivery)。

当前入口是 `rear-field`，配置是 `field-session.json`，控制 bundle 是 `bundle-deploy-v11.json`。Wuji 接 G2 本体；4090 经现有 GDT／CoRobot 执行链统一发送固定右臂和右手20关节目标。任务仅为固定腕姿、人工摆刀、独立持刀、推动滑块实测超过20mm并保持约1秒、卸载结束。

软件入口和新增会话保护已离线通过；尚无真机结果。现场映射、安装标定、时钟、驱动后处理及停止语义须与本体实际版本对应。缺这些事实时程序会拒绝运动，不使用 fixture、零位猜测或其他任务姿态绕过。

## 1. 谁负责执行，与原手册的差异

原手册流程“进入 field 容器 → policy server 等待 → GDT连接本体和server → PolicyTaskServer → 开始／复位”适用于示例PI任务。本项目保留容器、GDT本体连接、Forge扩展和CoRobot，使用已经实现的 controller／remote_env 路径：

`rear-field serve 等待 → GDT连接本体 → rear-field mode 配置/启动 remote_env → 只读核对 → rear-field start → 原ArtGym连续控制器 → CoRobot点动作 → 本体执行组件`。

Forge 的 `PiServerRunner._run_server()` 使用 CoRobot `PolicyServer`。已安装0.2.2的该协议仅处理 `infer/reset`，没有动作接受回执；连接本身不调用 reset。`PiRobotInferrer.reset()` 在未设置初始化文件时返回None，设置时返回其他任务的双臂/双手初始化轨迹。实际GDT按钮对应的客户端实现不在取得的源码中，不能推断“暂停”是否停止驱动或“开始”是否先自动复位。

同一Forge已有 `CorobotSDKController`，其环境使用 `init_remote_env` 的 `/system/status`、`/system/configure`、`/system/start`。本项目入口复用这套模式合同，直接使用真实 `RemoteEnvClient.execute_point_action`，每周期接收RPC结果后再提交目标历史。没有PI归一化、delta变换、丢6帧或复制动作块。

**相对原手册只改变控制启动位置：本项目启动 Forge controller 而非8999 PolicyTaskServer；GDT继续连接本体，模式与开始通过已实现命令完成。不要连接旧状态server，也不要在本会话中选择 PolicyTaskServer 或点击其推理/复位。** `remote_env` 是源码确认的模式标识；没有原截图，本文不编造GUI选项或按钮名称。HTTP命令可完成模式设置，无需自行设计接口。

动作最终由本体remote_env背后的GDK／手臂驱动组件执行；Python客户端0.2.2不是该驱动的源码。RPC成功表示接受点目标，不表示编码器到位、驱动没有插值或电机已经失能。

## 2. 部署文件与环境

公开版使用示例挂载：宿主机 `/srv/wuji-field` 对应容器 `/work`。先核对实际挂载；不同则相应调整以下路径。使用新目录，保留当前v5部署与现场Forge修改。

**宿主机终端：**将两份当前包、恢复脚本及SHA256SUMS放入 `/srv/wuji-field/rear-delivery`，然后执行：

```bash
cd /srv/wuji-field/rear-delivery
sha256sum -c SHA256SUMS
docker ps -a --filter name=field
docker inspect --format '{{.Image}} {{.HostConfig.NetworkMode}} {{json .Mounts}}' field
```

正常条件：校验通过，field为原有容器，挂载如上，网络为host。只有容器停止时执行 `docker start field`；随后 `docker exec -it field bash`。host网络无需再映射8999。不要重建容器、拉新镜像或运行训练。

**容器内终端A：**以下假设已验证的v5 ArtGym基础位于 `/work/artgym-rear`；若实际在别处，只替换恢复命令的 `--base`。它必须含原有权重，不能拿未验证训练目录替代。

```bash
cd /work/rear-delivery
python3 restore_wuji_rear_deployment.py --base /work/artgym-rear \
  --overlay rear-v6-deployment.tar.gz --destination /work/artgym-rear-v6 \
  --bundle-path research/rear-sim2real-20261009/bundle-deploy-v11.json
mkdir /work/wuji-rear-private-v6
tar -xzf wuji-forge-rear-v6-private.tar.gz -C /work/wuji-rear-private-v6
```

正常条件：恢复回执 `all_dependencies_sha256_match=true`，504项依赖一致，权重复用。私有包是独立Forge扩展副本，不覆盖 `/work/forge-universal`。

使用现有ArtGym Isaac Gym／Torch推理解释器和已安装CoRobot0.2.2的Python3.10解释器，两者分别输入一次。推理环境必须先导入Isaac Gym再导入Torch。以下输入的是**容器内**实际路径，不能使用宿主机路径：

```bash
read -r -p '现有ArtGym推理Python绝对路径: ' INFERENCE_PYTHON
read -r -p '现有CoRobot Python3.10绝对路径: ' COROBOT_PYTHON
"$COROBOT_PYTHON" -c 'import importlib.metadata as m; print(m.version("corobot-client-cpp"),m.version("agibotforge"))'
```

正常输出为 `0.2.2 0.43.0`。若现场缺这个独立环境，可创建私有包内的 `.venv`，使用包内两个wheel和 `requirements-bridge.txt` 安装；不要改推理环境：

```bash
python3.10 -m venv /work/wuji-rear-private-v6/.venv
/work/wuji-rear-private-v6/.venv/bin/python -m pip install \
  /work/wuji-rear-private-v6/packages/corobot_client_cpp-0.2.2-py3-none-any.whl
/work/wuji-rear-private-v6/.venv/bin/python -m pip install --no-deps \
  /work/wuji-rear-private-v6/packages/agibotforge-0.43.0-py3-none-any.whl
/work/wuji-rear-private-v6/.venv/bin/python -m pip install \
  -r /work/wuji-rear-private-v6/requirements-bridge.txt
COROBOT_PYTHON=/work/wuji-rear-private-v6/.venv/bin/python
```

这只是缺环境时的备选安装，未宣称该现场容器已装好venv工具。失败保留输出；现有合法环境可直接使用。

由现场同事确认本体WebSocket地址和system HTTP地址；使用现场确认的地址，不能照抄其他任务的示例。8891/8890分别是包示例的WebSocket/HTTP端口，不是4090 SSH地址，也不是8999 policy server。确认后输入：

```bash
read -r -p '本体remote_env WebSocket主机/IP: ' ROBOT_HOST
read -r -p '本体remote_env WebSocket端口: ' ROBOT_PORT
read -r -p '本体system HTTP根地址(含端口): ' SYSTEM_HTTP_URL
cd /work/artgym-rear-v6
"$COROBOT_PYTHON" /work/wuji-rear-private-v6/rear_field.py configure \
  --artgym-root /work/artgym-rear-v6 --inference-python "$INFERENCE_PYTHON" \
  --remote-host "$ROBOT_HOST" --remote-port "$ROBOT_PORT" \
  --system-http-url "$SYSTEM_HTTP_URL" --container field
```

生成 `field-session.json`、`field-work/profile.json` 和 `./rear-field`。随后所有终端都只用 `./rear-field`，解释器、环境、路径由配置恢复，无需重新export或拼接旧版本命令。原策略、权重、参考、补偿及30Hz语义保留。

## 3. 只读采集、合同绑定与准备

打开GDT，按已提供手册连接本体。先运行一套只读采集；若执行插件源码/配置有实际目录，可在同一命令加 `--source-root 那个目录`：

```bash
./rear-field collect --output field-work/capture-01
```

它保存 `capture.json`、`installed-execution.json`、`robot-read.json` 和阶段日志；包含包版本、相关组件路径/哈希/关键字行号、system状态、原始反馈、主机时间窗口和本体states时间戳。不会configure、start、reset或发关节目标。读取失败也保存已取得的证据。容器没有docker命令时会记录容器元数据错误，宿主机第2节输出用于补充。

正常反馈须有 `hand_joint_states[40]`、`arm_joint_states[14]`、头3和腰5，时间戳严格增加。右手20槽的真实命名/编码器来源、rad单位、绝对动作语义和时钟仍由驱动或既有记录核对；只有数值形状不够。如果remote_env尚未运行，采集可以失败并保存原因；仅在空手和现场授权下完成第4节mode后重采一次。

把现场已有安装/标定/执行事实填入 `field-work/profile.json`；模板预填项目命名和地址，未知硬件值为null。不是要求新写接口或重新搜集整套GDT教程。

- 手部state_names/state_indices和action_names独立排列；符号、绝对零位、硬件限位及速度按模型20关节顺序填写。观测必须为实测编码器，目标不能冒充反馈。
- 右臂模型名为idx61…idx67_arm_r_joint1…7，数字61…67不是数组槽位；绑定实际右臂7槽、符号零位、限位/速度。填写实际头/腰保持位置、基座旋转和法兰到手的安装旋转，不能默认现场躯干为零。
- 执行记录须说明手部归一化/增量/插值/滤波/限幅、有效频率、点动作过期和停止规则；请求period不是实测频率。硬件速度必须覆盖原完整轨迹，否则拒绝，不放慢5mm或完整动作。
- 确认states为可比较UNIX ns、同步误差不超过5ms。每周期检查反馈年龄加误差不超过33.33ms。跨机单调时钟不能直接相减。

每项evidence引用现有真实记录的文件、SHA256和来源；同一记录可覆盖多项。不得复制离线profile或使用 `--fixture`。文件移动或修改后重新setup绑定。

```bash
./rear-field setup
```

正常输出 `Setup complete`。`field-work/active` 指向当前配置、人工尺对齐的placement先验、完整命名目标和envcheck。环境/504项SHA/速度/目标走廊检查均通过才继续。setup不连接机器人或运动；不读取PI0.5 norm_stats。命名表区分原hold预载、15mrad reserve后的实际目标与实测值。

## 4. 启动程序、模式与空手初始化

现场同事确认手为位置模式、供电/驱动正常、手和右臂唯一写端，并确认本体过期及停止规则。刀此时不在手里。`INFER_INIT_POSITION`采用S1的**取消设置**方式；S2启用的雪碧/JD初始姿态不适用：

```bash
unset INFER_INIT_POSITION
./rear-field serve --motion-authorized --empty-hand-confirmed
```

终端A正常输出 `waiting_start`、`No target sent yet`，此时未建立运动连接或发目标。它启动实际Forge ArtGym入口，随后由原完整控制器运行；没有8999动作server。

**容器内终端B：**

```bash
cd /work/artgym-rear-v6
./rear-field mode --motion-authorized --empty-hand-confirmed
./rear-field collect --output field-work/capture-ready
./rear-field status
```

mode先查状态，需要时才POST配置 `remote_env` 和开始，保存前后回读。正常条件为 `current_mode=remote_env`、`instance_running=true`。重复mode不重启已运行实例；会话已经开始或写端锁被占用时拒绝mode。配置/启动本体可能运动，故仅空手执行。GDT用于连接和监看，不再触发另一个PolicyTaskServer写端。

只读反馈和现场合同满足后，可按现场同事要求空手核对一个已命名关节的小响应；joint=17为模型顺序的拇指第二关节。它保持当前右臂，不做初始化，不能代替绝对零位证据：

```bash
./rear-field check --motion-authorized --empty-hand-confirmed \
  --joint 17 --step-rad .01 --seconds 2
```

确认方向/幅度与已有标定一致后：

```bash
./rear-field start --motion-authorized --empty-hand-confirmed
```

这才开始运动：从实际右臂姿态做有界quintic过渡，每条统一点命令携带右臂和右手目标，其他部位省略保持。连续5帧编码器到位及FK/重力检查通过后才打开手进入 `place-1`。右臂角容差0.02rad，重力方向检查0.03rad；它们不是已证实的握姿泛化容差。未控左臂/头/腰偏移超0.02rad会中止。

重复start返回 `already_started=true`，不再初始化、不清历史、不改受载目标。进程重启没有可靠持刀目标记忆，必须先托刀取下，再使用新输出目录空手启动。不要把受载编码器q当新目标消掉预载。

## 5. 人工摆刀、合拢和撤托

确认 `./rear-field status` 的gate为 `place-1`，固定腕姿实测到位后才摆刀。查看私有包 `field-materials/placement-ruler.png`、`side-annotated.png`、`thumb-slider-annotated.png`、`mounting.png`；这些是仿真渲染/标尺，非实物照片。

刀144×19×10mm、55g，滑块32×7mm；局部+z从刀尾到刀尖，x沿宽度、+y朝滑块外法向。滑块近端距刀尾30mm、中心46mm。拇指指腹落在凸起内部，食/中指承托刀中前段，小指承托刀尾。手工托住刀尾，按图确认布局：

```bash
./rear-field next --gate place-1
```

合拢3秒，到 `withdraw-1` 时缓慢撤去承托，确认无滚动或持续滑移；承托完全撤去后：

```bash
./rear-field next --gate withdraw-1
```

同一连接继续独立保持并采历史。目标含预载，编码器与目标的差不等于真实力。人工尺估计不是实时视觉；标称接触边距约0.35mm不代表已经达到该摆放精度。

## 6. 响应检查与必要一次短推

会话自动做拇指第二关节0.01rad局部往返、恢复原hold，后台分析时主连接继续保持目标。终端给出 `field-work/session-01/analysis/response.png` 和 `analysis.json`，gate为 `response-review-1`。

检查方向、编码器响应幅度、静态偏置、恢复偏置、时序、近景接触和侧面滚转。程序会拒绝无可测响应或响应周期超过33.33ms；位置记录不能可靠辨识纯延迟、刚度或力。无明确异常才确认临时模型补偿和短推：

```bash
./rear-field next --gate response-review-1
./rear-field status
./rear-field next --gate prepare-probe-1
```

先等status确实显示 `prepare-probe-1` 再发第二条确认；过早或错误gate会拒绝。预热期间同一连接保活，推理预热输出丢弃，随后重采50帧实际反馈历史。

5mm probe保留完整35mm参考的原前缀速度，约前4mm/1.0398秒与完整动作一致，随后才用约0.1943秒平滑减速。它没有通过明显放慢掩盖动态问题；短推通过也不能证明全段可靠。尺/视频检查实际行程、滚转、滑移和保持；结果gate为 `result-probe-1`。明确失败就托刀并按第9节停止，不重复短推或自动增压/训练。

通过后：

```bash
./rear-field next --gate result-probe-1
```

## 7. 卸载、复位滑块和重新摆刀

到 `unload-1` 时仍保持原受载目标。托住并完全取下刀，手空后把滑块近端人工复位刀尾30mm，再确认：

```bash
./rear-field next --gate unload-1
```

此时才进入空手状态和第2次摆放；同一网络连接及最近成功目标保留。为重新放置的物体建立新策略状态/估计/历史，固定右臂不重新到位。绝不能从probe末态直接重置参考时钟跑完整动作。

按第5节再次摆刀/合拢/撤托，分别等待对应gate后执行：

```bash
./rear-field next --gate place-2
./rear-field next --gate withdraw-2
```

## 8. 完整推动与卸载结束

确认第2次独立持刀稳定，status显示 `prepare-push-2` 后：

```bash
./rear-field next --gate prepare-push-2
```

原控制器以30Hz请求完整35mm并保持；实测成功标准是滑块相对刀柄移动**超过20mm且独立保持约1秒**，用尺和连续视频判定，不能用模型参考或RPC回执代替。到 `result-push-2` 后记录结果；通过后：

```bash
./rear-field next --gate result-push-2
```

到 `unload-2` 时托刀、完全取下，确认空手再执行：

```bash
./rear-field next --gate unload-2
```

正常输出finished和summary，网络流结束。程序不调用其他任务reset，不自动全身回零。右臂和手最终是否保持/点过期由本体规则决定，现场同事须按已确认设备流程停止；**结束网络流不等于电机失能**。summary中的 `physical_stop_confirmed=false` / `disable_request_sent=false` 是如实报告。

## 9. 暂停、复位、失败和日志

容器终端B可操作同一会话：

```bash
./rear-field status
./rear-field pause
./rear-field resume
./rear-field stop
```

pause冻结阶段推进，同一连接每周期重新下发最近RPC接受目标；resume延续原目标、历史和摆放代数。空手到位过渡不支持pause，支持软件stop。暂停中next被拒绝；同名gate只能确认一次。最好在稳定等待阶段暂停，现场本体停止规则必须已核实。

`rear-field reset`始终拒绝外部自动复位，并提示卸载门操作。GDT连接/断开不触发本项目初始化；GDT切模式、暂停本体执行实例或断开驱动导致状态失效时，本控制器中止，不自动重连复位。无法从当前源码确认GDT的GUI暂停/急停/复位绑定，持刀期间用本项目pause，危险或故障由现场同事操作实际停止/急停。

stop/Ctrl+C只是软件停止请求，不能宣称物理停止。先托住刀，再按现场设备停止流程处理；故障后取刀，保存日志再空手重启。不要开第二个stop/USB写端、重新点击PI任务开始或让手自动打开。

日志在 `field-work/session-01`：`raw_target_rad` 为完整控制器输出，`issued_target_rad` 为实际RPC接受点目标，`encoder_model_rad` 为真实反馈的20D映射；`corobot-unified-rpc.jsonl` 保存原请求/响应/消息哈希/ACK时间，`write_timing`关联receipt_sequence。驱动插值后的瞬时电机目标目前无读回字段，单独标为未确认。`timing.jsonl`、summary报告周期耗时，operator-events记录启动/暂停/阶段确认，不把infer返回当执行成功。

## 10. 仍需现场确认的最少事实

只集中补两类现有资料：①上述一次capture，加本体当前版本处理 `execute_point_action/right_effector/hand_joint_states` 的组件名称、版本和相关实现/配置或运行记录，确认20关节名称/单位/来源、绝对语义、后处理/频率和过期/停止；②当前G2/Wuji的零位、硬件限位/速度、安装/固定体对应及时钟同步记录，填同一profile。无需重找GDT教程、训练数据、私钥或整个SDK。

它们分别影响setup/只读校验、第一次start、受载30Hz与退出；没有设备不能宣称这些现场事实已通过。软件21项新入口检查、既有20项合同/380帧对齐/1174周期完整会话均为离线证据；32.209mm/1.033秒物理结果仍仅适用于假设10ms过渡，不是现场插值参数。本轮未重训、未重跑完整矩阵或物理仿真。v3 USB、v4状态server和v5分散命令已移入历史指南；本文件是当前唯一操作流程。
