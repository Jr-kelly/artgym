# 完整平放桌面取物已接入既有 B

新增连续 98 秒仿真通过：整把刀平放在桌面，机器人推移并夹实心端盖，受载搬运到可取位置，三指协同释放，横向退出避免勾刀，然后执行原 B 的取物、换握、独立离桌推动及保持。阶段间没有设置刀、滑块或机器人状态。

标称主动位移 29.0535 mm；推动前滑块位移 0.000338 mm；保持窗最小主动位移 29.0390 mm、波动 0.0290 mm。操作期整刀最低离桌 87.58 mm、桌面接触 0，每个实际物理帧均有非拇指承托。

B 保留 actor、几何接触参考、路径切向补偿、压力120、承托与定时保持，50 帧 q/action 历史来自本次运行。新增的是 76 秒桌面前置动作及一次实际放置后位姿驱动的原 B 路径适配，推动仍使用原 B。actor SHA256 `6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e`。

输入来源为显式 sim_oracle；保留 robot_base/m_rad 位姿文件接口 `--postpush-pose-input`。真实视觉未接、未运行真机。0.73549875 N 是已有被动制动模型容量，实际总轴向接触力缺测，不能当作实物推力容量。

## 复现

在既有依赖环境与仓库根目录运行（新输出目录）：

```bash
source runs/contact-transfer-20261006/env.sh
python -m scripts.run_wuji_flat_connected --output runs/flat-table-20261006/reproduce-connected-fresh
```

新增入口、配置和证据包从 Release v2 下载后在仓库根目录解压。既有环境、G2/Wuji 资产、R800/残差权重及旧 B 配置复用先前发布依赖，不重复构建。

开发短片段仅用于确定三指释放／退出路线，不作为完整成功证据。主证据是 `runs/flat-table-20261006/development/continuous-existing-B-v1-20261006/simulation/connected-evaluation.json` 和同一 episode 的原始视频，2940 帧、30 fps。

- [远近同步并排视频](https://github.com/Jr-kelly/artgym/releases/download/wuji-flat-table-progress-20261006-v2/flat-connected-synchronized.mp4)
- [完整全景](https://github.com/Jr-kelly/artgym/releases/download/wuji-flat-table-progress-20261006-v2/flat-connected-wide.mp4)
- [完整近景](https://github.com/Jr-kelly/artgym/releases/download/wuji-flat-table-progress-20261006-v2/flat-connected-close.mp4)
- [内嵌播放报告](https://github.com/Jr-kelly/artgym/releases/download/wuji-flat-table-progress-20261006-v2/flat-connected-report.html)

必要局部验证正在执行：初始 x/y 各 +1 mm、yaw +0.5°并结合放置后位姿估计 x +1 mm；原几何 1.25 N；已有 mid 尺寸／滑块位置变化加 1.25 N、1帧延迟及噪声。各例沿同一 A 控制和 actor，无人工逐例调姿。结果完成后写入此处；当前不声称全范围泛化。
