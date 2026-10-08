# 已有运行环境中的复现

本地完整工作根 `/data/research/artgym-experiments-20260921/rear-sim2real-20261009`，基于原 contact-transfer 恢复副本；这次新增只在此独立副本。保留已许可的 Isaac Gym，不升级原训练 Python3.8 环境。SDK 放在独立 Python3.10 venv，已安装1.8.0；从 SDK 子进程清除训练库路径。

```bash
cd /data/research/artgym-experiments-20260921/rear-sim2real-20261009
bash scripts/g2_local_python.sh -m scripts.run_wuji_rear sim --output runs/reproduce-rear --video
bash scripts/g2_local_python.sh -m scripts.validate_wuji_rear_software
```

无需真机、无新训练。默认配置固定为 bundle-deploy-v6。评分在 `result.json`；命令退出0仅表示完成，不能替代 `passed`。每次使用全新输出路径，保留失败。仿真一次12.667s，3s合拢／撤临时承托，3.667s实际保持／预热／新50帧历史，6s推动／保持。已有0.7355和1.25 N能力参见主报告；失败响应／延迟条件见RESULTS，不重复矩阵。

如换机器，先用已有 [contact-transfer 恢复说明](../contact-transfer-20261006/REPRODUCE.md) 恢复基础运行环境／权重／资产，再覆盖本轮公开增量。运行 `load_bundle` 会验证所需文件哈希，不自动下载或替换另一个模型。离线SDK检查用实际Python3.10路径或通过 `--sdk-python` 指定等价环境：

```bash
python3.10 -m venv /你的SDK环境
/你的SDK环境/bin/pip install 'wujihandpy==1.8.0'
```

实时硬件流程请按 [FIRST-HARDWARE-SESSION.md](FIRST-HARDWARE-SESSION.md)。`--fixture` 只构造SDK形状模拟对象，不能用于物理成功或设备时延结论。不同GPU的接触数值可能不同；不能仅复制原来的小数。

## 本轮下载包与恢复检查

下载 [本轮 Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-rear-sim2real-20261009-v1) 的 `rear-runtime-overlay.tar.gz`、`rear-evidence.tar.gz`、`rear-video-report.zip` 和 `ASSET-MANIFEST.json`，逐个核对 SHA256。运行增量只覆盖本轮源码、配置和新增材料，旧 Teacher／Student／残差权重继续从上述已验证基础恢复，未重复打包。

在已恢复的 contact-transfer 基础**新副本**根目录解压运行增量。原始证据包也按根目录解压；视频包解压后打开 `research/rear-sim2real-20261009/review.html`。不解压到正在训练或包含用户改动的原项目。随后运行上面的软件验证，它对全部 340 个固定依赖逐个核验 SHA256；缺文件或内容不符直接报错。本轮 `RESTORE-OVERLAY-VERIFICATION.json` 核对了归档增量＋现有基础组合的全部依赖，未把文件恢复检查算作额外物理试验。

完整已安装推理包版本见 `RUNTIME-CONTRACT.json`（本机 Torch 2.1.0+cu118、NumPy 1.23.5、Python3.8.20）；不根据旧报告中的环境示例降级。本轮没有发行 Isaac Gym、CUDA 或 SDK 安装文件；需使用已有授权运行环境。
