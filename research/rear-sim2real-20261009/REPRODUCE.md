# 已有运行环境中的复现

本地完整工作根 `/data/research/artgym-experiments-20260921/rear-sim2real-20261009`，基于原 contact-transfer 恢复副本；这次新增只在此独立副本。保留已许可的 Isaac Gym，不升级原训练 Python3.8 环境。SDK 放在独立 Python3.10 venv，已安装1.8.0；从 SDK 子进程清除训练库路径。

```bash
cd /data/research/artgym-experiments-20260921/rear-sim2real-20261009
bash scripts/g2_local_python.sh -m scripts.run_wuji_rear sim --output runs/reproduce-rear --video
bash scripts/g2_local_python.sh -m scripts.validate_wuji_rear_software
```

无需真机、无新训练。默认配置固定为 bundle-deploy-v7。评分在 `result.json`；命令退出0仅表示完成，不能替代 `passed`。每次使用全新输出路径，保留失败。仿真一次12.667s，3s合拢／撤临时承托，3.667s实际保持／预热／新50帧历史，6s推动／保持。已有0.7355和1.25 N能力参见主报告；失败响应／延迟条件见RESULTS，不重复矩阵。

如换机器，先用已有 [contact-transfer 恢复说明](../contact-transfer-20261006/REPRODUCE.md) 恢复基础运行环境／权重／资产，再覆盖本轮公开增量。运行 `load_bundle` 会验证所需文件哈希，不自动下载或替换另一个模型。离线SDK检查用实际Python3.10路径或通过 `--sdk-python` 指定等价环境：

```bash
python3.10 -m venv /你的SDK环境
/你的SDK环境/bin/pip install 'wujihandpy==1.8.0'
```

实时硬件流程请按 [FIRST-HARDWARE-SESSION.md](FIRST-HARDWARE-SESSION.md)。`--fixture` 只构造SDK形状模拟对象，不能用于物理成功或设备时延结论。不同GPU的接触数值可能不同；不能仅复制原来的小数。

## 本轮下载包与恢复检查

下载 [本轮 Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-rear-sim2real-20261009-v1) 的 `rear-runtime-overlay.tar.gz`、`rear-evidence.tar.gz`、`rear-video-report.zip` 和 `ASSET-MANIFEST.json`，逐个核对 SHA256。运行增量只覆盖本轮源码、配置和新增材料，旧 Teacher／Student／残差权重继续从上述已验证基础恢复，未重复打包。

在已恢复的 contact-transfer 基础**新副本**根目录解压运行增量。原始证据包也按根目录解压；视频包解压后打开 `research/rear-sim2real-20261009/review.html`。不解压到正在训练或包含用户改动的原项目。随后运行上面的软件验证，它对全部 343 个固定依赖逐个核验 SHA256；缺文件或内容不符直接报错。本轮 `RESTORE-OVERLAY-VERIFICATION.json` 核对了归档增量＋现有基础组合的全部依赖，未把文件恢复检查算作额外物理试验。

完整已安装推理包版本见 `RUNTIME-CONTRACT.json`（本机 Torch 2.1.0+cu118、NumPy 1.23.5、Python3.8.20）；不根据旧报告中的环境示例降级。本轮没有发行 Isaac Gym、CUDA 或 SDK 安装文件；需使用已有授权运行环境。


## v2 仅补短动作与分析

基于已有v1工作根，覆盖v2运行增量，默认配置改为bundle-deploy-v7；旧v6文件保留为历史pin，需用v1 Release或对应Git提交恢复旧源码后才能按旧哈希运行，不把旧哈希直接用于改过的新代码。

```bash
bash scripts/g2_local_python.sh -m scripts.run_wuji_rear sim --operation probe --output runs/my-short-probe --video
# 唯一诊断风险对照：
bash scripts/g2_local_python.sh -m scripts.run_wuji_rear sim --operation probe --delay-frames 1 --output runs/my-short-delay --video
# 同现场response激励：1秒静态、2秒0.01rad往返、1秒恢复
bash scripts/g2_local_python.sh -m scripts.run_wuji_rear sim --operation response --output runs/my-response
bash scripts/g2_local_python.sh -m scripts.analyze_wuji_rear_response --input runs/my-response --output runs/my-response-analysis
bash scripts/g2_local_python.sh -m scripts.validate_wuji_rear_diagnostics
```

诊断算法测试复用已保存的新probe／旧v6命令，因此应先解包对应证据资产；它不计作物理成功。相同完整控制路径的380帧旧编码器重放指令零差异，完整推进参数没有改动，未重跑矩阵或完整任务。最终343项依赖pin见v2/DEPENDENCIES。v2运行增量需要已经恢复并验证的v1根；v2证据仅包含本轮三条物理仿真、离线接口／时间与小算法测试，旧完整视频直接从v1复用。

v2增量与新证据下载：[wuji-rear-sim2real-20261009-v2](https://github.com/Jr-kelly/artgym/releases/tag/wuji-rear-sim2real-20261009-v2)。恢复顺序：已验证v1根 → v2运行增量 → v2原始证据；新视频包打开v2/review.html，旧完整视频仍用v1。
