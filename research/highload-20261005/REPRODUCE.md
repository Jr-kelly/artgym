# 复现本轮 G2 + Wuji 仿真

本轮是完整连续仿真与能力边界交付，不含真实机器人运动接口。默认 highload 工程候选未通过所有原评分；baseline 是保留的 V13 .35，通过记录与新候选分开。原评分没有改变。

## 既有环境中的入口

在仓库根目录，使用已安装 Isaac Gym 的兼容 Python：

```bash
python -m scripts.run_wuji_highload_selected --mode highload --output runs/my-new-highload
python -m scripts.run_wuji_highload_selected --mode baseline --output runs/my-new-v13
python -m scripts.run_wuji_highload_selected --mode capacity --output runs/my-new-capacity
```

每个输出必须是新目录。默认生成从桌缘取刀到两轮40mm命令的完整主视角及近景视频；`--no-video`只省略渲染。capacity 保留 .20 被动制动基础容量，加全操作期 .05N 平衡对向测试负载，不是原刀总轴向力或总阻力 .25N。

初始估计适配示例（fresh01 已是开发条件）：

```bash
python -m scripts.run_wuji_highload_selected --mode highload \
  --load .35 --detent .35 \
  --initial-estimate runs/traction-20261005/validation/fresh-inputs-v15/fresh01/once-estimate.json \
  --knife-asset runs/traction-20261005/validation/fresh-inputs-v15/fresh01/mobility.urdf \
  --hand-friction .75 --observation-noise .0003 --seed 2026100515 \
  --output runs/my-new-fresh01
```

所有资产使用同一初始几何适配机制；物理资产与负载标签不进入策略，不按标签挑权重。适配后先执行原73点取刀与81点40mm行程证书，不跳过失败。脚本演示、冻结后验证、同机恢复与真机结果不可混称。

## 空目录恢复（复用既有依赖，不重复下载大包）

从 `wuji-g2-wrap-force-20261005-v1` 获取或复用：

- wrap-runtime.tar.gz：`3641e30850d88a41a5db4c385ff06d50ca321bc1f47e6527cd23fdcbd1a43fab`
- wrap-learning-state.tar.gz：`519d9dc52d7cb1091da79901268933e8ccabfa908425bd1b1ccdc98ec84039b4`

从 `wuji-g2-traction-20261005-v1` 获取或复用 traction-overlay.tar.gz：`720883ee29b204e7e8d5cdc023191f451fd6118f3347f3b745b5420a630c1e67`。
本轮Release提供 highload-overlay.tar.gz、文件SHA清单及恢复脚本。先解开本轮覆盖包的scripts，或使用本轮代码分支运行：

```bash
python -m scripts.restore_wuji_highload \
  --baseline-dir /path/to/wrap-archives \
  --traction-overlay /path/to/traction-overlay.tar.gz \
  --overlay /path/to/highload-overlay.tar.gz \
  --destination /path/to/new-empty-directory --run
```

恢复检查先核对依赖与每个覆盖文件的SHA，然后真实运行一次capacity完整任务；`RESTORE-RESULT.json`保存原评分与退出码。这是可恢复性检查，不是新的独立泛化样本。

Isaac Gym授权runtime不在包内。已验证本地Python `/home/agiuser/miniconda3/envs/artgym/bin/python`，远端 `/home/wangjiarui/artgym-runtime/bin/python`。运行需让PATH指向该runtime/bin、LD_LIBRARY_PATH包含runtime/lib，PYTHONPATH包含恢复目录及rl_games，设置PYTHONNOUSERSITE=1、OMP_NUM_THREADS=4、MKL_NUM_THREADS=4。不得混装其他Python的torch；仿真模块先导入Isaac Gym再导入torch。GPU差异和物理接触非线性可能造成微小轨迹变化。

## 结果与代码

`DELIVERY-RESULTS.json`包含原端点评分与每段真实位移、接触、转动；`highload-evidence.tar.gz`保存轨迹/运行身份/失败、240Hz负载证据和利用率采样。`FROZEN-ENGINEERING-CANDIDATE.json`和`FROZEN-CAPACITY-CANDIDATE.json`固定执行命令及S120 SHA。未做新训练，R800/teacher/normalizer继续来自原依赖包。

`wuji_scheduled_thumb_reference.py`的时序、滤波和参考更新可选项，以及压力适配的`operation_updates`/`operation_normal_correction_coordinates`只用于本轮明确标注的消融，最终工程候选不启用。新支撑几何准备脚本与被拒证书保留供复查。原criterion仅增加跨机器路径解析；评分常量、时间窗和比较符一致。

代表性第三轮失败连续46秒，原始全轨迹评价保留。`first-two-cycles`只是同一轨迹前36秒的附加诊断，不能当成新运行或挽救原46秒成绩。完整媒体报告与原MP4单独提供，私人照片/手动视频不发布。
