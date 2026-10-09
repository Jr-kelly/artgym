# 当前v5网络通路

先读v5/REPORT.md、VERIFICATION.json；当前bundle-deploy-v10及统一网络后端。复用原模型和合法380帧输入；制造商实际客户端/私有注册入口、集中field和现场命令随私有包。环境是原Isaac Gym/Torch Python3.8推理＋独立Python3.10 CoRobot；无PC USB发现前提，无PI0.5训练。本轮仅1条条件10ms过渡的标称物理，不重复矩阵。旧源代码／权重／旧失败／视频完整保留。

自研包恢复时使用现有工具的 --bundle-path research/rear-sim2real-20261009/bundle-deploy-v10.json。现场从只读执行组件/状态capture开始，再绑定实际profile；未知名字/单位/clock/执行后处理不能靠offline fixture填写。下面旧指令属于对应版本历史，当前启动按私有v5指南。

<!-- V5_REPRODUCTION -->
# v4续接

当前bundle-deploy-v9.json，控制核心/权重不变。公开部署包与私有制造商桥接包分开；私有协议源码不进入公开归档。包工具使用 `--bundle research/rear-sim2real-20261009/bundle-deploy-v9.json --revision v4`；恢复工具使用 `--bundle-path research/rear-sim2real-20261009/bundle-deploy-v9.json`。复用v3现场环境和旧权重，无需依次覆盖旧版本、重训或重做矩阵。当前交付只证明协议软件/离线会话，现场仍有明确待验项。

# 当前v3部署恢复与必要验证

当前运行配置 `bundle-deploy-v8.json`，历史v6/v7及其证据保留在对应Git提交／旧Release；改过的源码不能使用旧pin。未训练、未重跑矩阵。实机G2接口仍阻塞，不能宣称整套可直接上机。

下载 [v3 Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-rear-sim2real-20261009-v3) 的 `rear-v3-deployment.tar.gz`、`restore_wuji_rear_deployment.py` 和 `ASSET-MANIFEST.json`，校验SHA。现有已验证 contact-transfer／ArtGym基础根持有原Teacher／Student／残差和资产；新脚本组合基础＋**一个**当前包，不需要推断v1/v2增量覆盖顺序：

```bash
python3 restore_wuji_rear_deployment.py --base "$ARTGYM_BASE" \
  --overlay rear-v3-deployment.tar.gz --destination "$DEPLOY_ROOT"
cd "$DEPLOY_ROOT"
python3 -m scripts.wuji_rear_field configure --config field.json \
  --inference-python "$INFERENCE_PYTHON" --sdk-python "$SDK_PYTHON" \
  --initial-estimate research/rear-sim2real-20261009/v3/initial-estimate.json
python3 -m scripts.wuji_rear_field envcheck --config field.json --output field-env.json
python3 -m scripts.wuji_rear_field run --config field.json discover
```

恢复不包括第三方受许可Isaac Gym；当前策略仍需它及现有Py3.8/Torch2.1环境，SDK为独立Py3.10/wujihandpy1.8.0。准确依赖、首次使能、校准、摆刀、连续持刀／卸载重启、停止和G2所需资料全部见唯一 [现场指南](FIRST-HARDWARE-SESSION.md)。配置不得将venv python软链接解析成系统解释器。不要修改原训练环境。

本机复现命令（环境变量填实际路径，不绑定开发机个人目录）：

```bash
export WUJI_INFERENCE_PYTHON="$INFERENCE_PYTHON"
bash scripts/g2_local_python.sh -m scripts.validate_wuji_rear_deployment \
  --sdk-python "$SDK_PYTHON" --old-commands "$SAVED_NOMINAL_COMMANDS" \
  --output runs/my-contract-check
python3 -m scripts.wuji_rear_field run --config field.json session \
  --fixture --motion-authorized --empty-hand-confirmed --output runs/my-offline-session
# 可选复现唯一新全段物理检查；本轮已完成，不自动重跑：
python3 -m scripts.wuji_rear_field run --config field.json sim \
  --output runs/my-full-physical-check --video
```

`SAVED_NOMINAL_COMMANDS` 是v1标称380帧 `runs/rear-sim2real-20261009/final/nominal-video-v6/commands.jsonl`，在本轮证据包也包含这一份复用输入。新包不重复旧巨型权重。SDK fixture没有真实G2、没有接触物理，也不代表现场USB时延。退出0不等于接触成功：物理仿真看result.passed，现场看G2到位读回、独立持刀、相对尺测>20mm／1秒和视频。

新目录实际推理／SDK证据在 `v3/PORTABLE-INFERENCE-VERIFICATION.json`；命名映射、坐标链、零位来源与限位／速度处理不能用文件哈希替代现场校准。当前24项软件检查、零指令差及一条共享会话物理全段足以覆盖本次实现变化，不追加全矩阵。
