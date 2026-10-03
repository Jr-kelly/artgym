# G2 + Wuji v1 本轮恢复与复现

最终候选、Release URL和哈希以源码内 `freeze.json` 与单独Release资产 `release-manifest.json` 为准。恢复到空目录，不覆盖原研究工作树。源码包仅含Git跟踪内容；用户的Franka修改和附件中的个人照片/视频不属于公开资产。

## 环境

实际验证运行时为Python 3.8、PyTorch 2.1.0+cu118、CUDA支持的Isaac Gym Preview 4和NVIDIA GPU。Isaac Gym是单独安装的依赖；本Release不重新分发该SDK。确切Python包记录见 `runtime-local-pip-freeze.txt` 和 `runtime-remote-pip-freeze.txt`。这两份是实跑环境记录，不应混合安装。首次运行需要可用C++编译器和Ninja构建GymTorch扩展；将当前Python环境的bin目录放在PATH前端。中文续接文档建议设置 `PYTHONUTF8=1`，避免C/ASCII locale读取失败。

## 恢复文件

下载本轮Release的 `release-manifest.json`、源码归档、权重与训练恢复归档，以及 `under-family-v1-assets-caches.tar.gz` 、`height-sensitivity-assets-v1.tar.gz` 和 `fresh-validation-assets-v1.tar.gz`。源码、权重、生成资产分别解压到同一个新的根目录，保留归档内的相对路径。其他数据、视频和工作回执包用于审阅与继续研究，推理无需一次解压全部训练数据。每个包的外部manifest列出精确文件路径、大小与SHA256；最终清单列出归档SHA256。先核对归档哈希，再运行。

R800是2076维SC-real编码器适配权重，必须同时保留指定teacher及其normalizer；不能把它当作独立actor。主候选还需P50残差权重和冻结的拇指几何参考。所有控制维度、坐标、递推和实际观测来源见 `ACTOR-CONTROL.md`。手20维按URDF关节名映射到G2机器人27维，手重力开启、原PD与总力矩限制保留。

## 完整仿真

完整命令见 `REPRODUCE.md`，全部332回合的固定命令另见 `frozen-validation-commands.sh`。连续runner从刀柄重心仍在桌面边缘内侧开始，约6.5mm侧边悬出以便手指从下方支撑；它不涵盖任意桌面中央摆放。0–8秒脚本接近/闭合，8–12秒抬升，12–16秒持稳，16–36秒同一物理回合完成两轮伸出、保持、缩回和保持。候选实际接管时刻以冻结配置为准。两类完整入口都只在初始回合设置物理状态，阶段之间不附着、不重置、不直接驱动滑块。

工程新增运行与起动幅值不等于实物总阻力；0.1N不是真实上限。未充分测量的滑块尺寸、质量/惯量、卡槽阻力和材料仍是近似。独立验证包保留全部初态、全部回合及实际视频。开发512几何、联合训练拟合、最终独立组合、脚本分支和部署离线回放分别报告。

## 继续训练与部署准备

训练恢复归档保存各已完成分支的实际末次checkpoint、Adam、CPU/CUDA/NumPy随机数状态和配置。`--updates`是绝对更新数。恢复优化状态后重新建立物理回合，不宣称PhysX/RNN物理状态逐位恢复。按实际末次记录继续；中间检查点与最终恢复点不同。

`replay_g2_continuous_policy`只对保存的关节/已发命令轨迹产生离线指令文件，已验证600帧完整操作的电机目标一致。它不连接硬件。真机需要另行标定SDK关节索引、方向和单位，校准有效力矩/压力含义，测量实物滑块阻力并完成现场验证；本轮没有下发真机动作。

## 清单验证与空目录恢复

将Release文件放到同一个ARTIFACTS目录，源码归档名为 `wuji-g2-source-final.tar.gz`，权重为 `models-and-recovery-final.tar.gz`。使用源码包中的恢复脚本，或者从Release直接下载同一脚本，执行：

```bash
python3 restore_wuji_robust_delivery.py --artifacts ARTIFACTS --verify-only
python3 restore_wuji_robust_delivery.py --artifacts ARTIFACTS --destination NEW_EMPTY_ROOT
```

默认恢复源码、权重、当前under几何、高度和新128个独立几何。`--all`同时恢复可选证据归档。每个原始回合和训练分支的语义由其report/identity决定；“包含于归档”不使训练资产成为独立验证。

## 最终下载后的执行核验

源码归档对应本地 `feb2118176893b1acf025abc1c9ad6b7b8a2cdcc`、GitHub `2e75dd3a5668ad1b18c73b9a8d6913ae5c2f28ea`，树 `0443626c55873dff9657a7ffa53eed659382c7ea`。最终交付分支/标签可以包含此后新增的下载核验、恢复重执行、比较/打包入口和报告；原1258运行文件及闭合上下文actor入口不变。后续核验入口随 `final-downloaded-recovery-evidence.tar.gz` 和最终Git树提供。主推理仍是154维P50；155维开发原型使用单独入口与head。

在实际GitHub下载的空目录恢复中，原生桌面连续demo再次成功（v68），600帧完整策略离线回放电机目标误差0。七组固定332条件的H200无图形恢复重执行与原4090录像验证另行报告，不能替代原204/332。另对实际下载的两个155维末次Adam/RNG执行有限34更新恢复，跨越完整36秒物理回合，只核验可恢复执行，不形成新候选分数。

传输和GitHub工具应使用系统环境；仿真所需 `LD_LIBRARY_PATH` 只赋给仿真Python子进程。把该变量传给系统SSH可能触发OpenSSL版本不匹配，已保存失败回执并用干净环境恢复文件传输。

全部17个最终归档已通过实际下载后的 `--all` 合并空目录恢复，主1258运行文件、冻结输入/权重以及155维入口/head仍精确一致。组合归档中的127份实际报告已检查，113份有权重引用，均有对应交付模型哈希；共有83个checkpoint路径。早期脚本诊断中的字符串 `None` 表示无残差权重，不是缺文件。主推理默认只需5个归档，其他数据与视频按需下载。

源码及证据归档中的报告/续接文档均是打包时快照。当前结果以 Release 直接附件 `FINAL-REPORT.md`、`FINAL-RESOURCE-AUDIT.json` 为准，后续发布回执及续接状态在交付分支最新 `WUJI_GOAL_HANDOFF.md`。源码归档的旧 PID/未发布状态不可作为当前事实。

原独立与恢复复跑的逐案例配对（同 env/实例/种子，332例）见最终Git树 `final-downloaded-paired-episode-agreement.json`，原始两组报告在对应独立验证与下载恢复归档中。部分逐回合 `scope` 字符串继承共享训练采集器模板；实际实验角色以顶层检查报告、冻结预登记和执行回执为准，原始字段保留。
