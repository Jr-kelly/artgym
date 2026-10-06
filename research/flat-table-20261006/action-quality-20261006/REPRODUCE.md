# 最小复现

1. 获取Jr-kelly/artgym的feat/wuji-flat-table-20261006最新源代码。需要Linux NVIDIA GPU及已配置的Isaac Gym环境。
2. 下载本Release的wuji-quality-final-increment.tar.gz，在仓库根目录解包。包内含必要新增源、引用路径/配置、原权重和本轮证据，不含私人附件或全部历史。
3. 原主机执行source runs/contact-transfer-20261006/env.sh；换机器时按此文件的Python/Isaac Gym配置调整实际安装路径。环境文件不是自动安装器。
4. python -m scripts.run_wuji_quality_connected --output <不存在的新目录> --case nominal

可选case为placement-error、placement-error-opposite、load125、mid-geometry；压力与适配由同一入口统一设置。mid按既有估计几何生成路径，没有逐例压力调参。不要用--recorded-handoff代替完整验证。

dependency-manifest.json为代码及运行输入SHA256；archive-files.json为包内文件SHA256；Release SHA256SUMS为上传资产SHA256。视频在本次完整原始运行产生，与trace配对；同步仅hstack，不剪辑。原环境入口、需要的私有安装路径和Isaac Gym依赖须由使用者安装；真机命令未提供或执行。
