# Wuji 美工刀滑块演示

这个分支包含演示的仿真运行代码，**无任何文字叠加的视频发布在 GitHub Release**。使用 **Wuji 右手，20 个关节**，
四指指尖托持刀柄、拇指操作滑块，刀头朝拇指/食指方向。

**这是预先求解手指轨迹、再通过物理接触驱动滑块的演示。**
视频没有使用训练好的 teacher/student，也不是实机实验。

## 视频和结果

- [下载或播放无文字 MP4](https://github.com/Jr-kelly/artgym/releases/download/wuji-knife-demo-v1.0.0/wuji-knife-demo.mp4)
- [视频封面](media/wuji-knife-demo/demo.png)
- [滑块位移与刀柄漂移曲线](media/wuji-knife-demo/metrics.png)
- [原始测量报告](media/wuji-knife-demo/report.json)
- [发布前独立重跑验证](media/wuji-knife-demo/verification.json)：单次仿真和渲染通过，测量指标与原报告一致。

录制时长 12 秒，960 × 720、30 fps。刀具收刀外形 **147 × 19 × 11 mm**，
总质量 **35 g**，尺寸来源和分件估计见 [knife_reference.md](knife_reference.md)。
录制结果：滑块最大伸出 **35.68 mm**，随后回到约零；刀柄最大漂移 **1.54 mm**。
采样中无掌部接触，无名指指尖偶尔离开刀柄。

## 安装

从新分支克隆即可运行本例，不需要生成物体/抓取数据的子模块：

```bash
git clone --branch demo/wuji-knife-fingertip --single-branch https://github.com/Jr-kelly/artgym.git
cd artgym
```

已验证环境：Linux、RTX 4090、Python 3.8.20、PyTorch 2.1.0+cu118、
Isaac Gym TacSL。准备 Python 环境，并按 [install.md](install.md) 的第 3、4 步
安装 PyTorch 与 Isaac Gym；然后安装这个演示需要的依赖：

```bash
conda create -n artgym python=3.8 -y
conda activate artgym
# 按 install.md 安装 PyTorch 和 Isaac Gym TacSL。
python -m pip install -r requirements-wuji-demo.txt
```

Isaac Gym 需单独安装，没有随分支打包。默认演示直接使用 Gym API，
不需要训练 checkpoint，也不需要安装本地 rl_games。

## 运行

在仓库根目录、已激活的仿真环境中执行：

```bash
MAX_JOBS=2 python -m scripts.wuji_knife_demo --no-overlay
```

输出位于 `tmp/wuji-knife-demo/`：`demo.mp4`、`demo.png`、`metrics.png`、
`report.json`、`rollout.npz`、初态和关节目标轨迹。发布的视频保存在 Release；`media/wuji-knife-demo/` 保存封面、报告和测量数据。
`--no-overlay` 去掉全部标题、时间、尺寸与底部说明，直接输出原始相机画面。

默认省略 `--no-overlay` 时仍可生成带调试文字的视频。

若只验证物理运动而不渲染：

```bash
MAX_JOBS=2 python -m scripts.wuji_knife_demo --no-render
```

也可以用 `--cycles 3` 检查连续往返；只有单次往返属于本分支随附视频的验证结果。
程序会检查资产哈希、关节顺序、运动范围、刀柄漂移、指尖支撑和刀头方向，
未满足演示阈值时返回错误。默认使用刚体接触对统计，请保留默认 CPU tensor pipeline。
PhysX 本身仍使用 GPU。

如果系统没有 MP4 播放器，可以启动本地 HTTP 服务后在浏览器打开：

```bash
python -m http.server 8767 --bind 127.0.0.1 --directory tmp/wuji-knife-demo
```

访问 `http://127.0.0.1:8767/demo.mp4`。在远端运行时，需要先把端口转发到本机。

## 代码与资产

| 文件 | 用途 |
|---|---|
| `scripts/wuji_knife_demo.py` | 默认入口：检查资产、展开预设轨迹、运行仿真和生成曲线 |
| `scripts/run_wuji_knife_demo.py` | PhysX 场景、位置目标控制、接触统计、视频输出 |
| `scripts/wuji_kinematics.py` | Wuji 正/逆运动学 |
| `scripts/build_wuji_knife_demo.py` | 刀具建模和抓姿求解工具 |
| `scripts/refine_wuji_knife_grasp.py` | 拇指接触点与关节目标求解 |
| `scripts/prepare_wuji_slim_demo.py` | 细身模型转换和离线轨迹搜索工具 |
| `assets/demo/wuji_knife/fingertip_preset.yaml` | 本视频使用的初态、49 个完整关节路点及仿真参数 |
| `assets/demo/wuji_knife/slim/` | 细身刀具 URDF 和尺寸/质量说明 |
| `assets/hands/wuji_artbot/` | 从 ArtBot 导出的右手 URDF、视觉/碰撞网格和来源哈希 |
| `media/wuji-knife-demo/` | 无文字封面、报告、曲线、录制时的初态和轨迹 |

默认运行只需要已包含的资产和预设。离线搜索脚本保留了制作过程中的工具；
其中 `prepare_wuji_slim_demo prepare` 需要原研究工作区的 `knife_wuji_paper/000`
模型和有效抓取缓存，这些训练数据不属于本视频发布包。复现随附视频无需运行搜索。
`preset.yaml` 和 `slim_preset.yaml` 是早期版本，默认入口使用 `fingertip_preset.yaml`。

原始轨迹来自离线搜索候选 22；已选候选在本分支的单环境运行中编号为 0。
`report.json` 是无文字视频重跑时的物理记录；随附 `manifest.json` 记录 Release
视频及必要代码、资产的 SHA-256。

## 物理模型和控制

手腕固定，刀柄是受重力影响的自由刚体；预览关闭手自身的重力。
仿真按 120 Hz 插值发送手指位置目标，刀具滑动关节的驱动刚度为零。
滑块运动由拇指接触产生，刀片外观随滑块移动。

本例采用刀具表面摩擦系数 3、滑块阻尼 0.3；这些是预览参数，
与论文训练的名义滑块阻尼 1000 不同。启用跨手指及远端指节对掌部的碰撞。
手的质量和驱动参数来自 ArtBot USD，碰撞网格由视觉网格近似生成。
刀片仅有视觉几何，未模拟切割、锁止或按压解锁机构。

本分支的阈值用于验证这个脚本演示。部署真机仍需要有效策略、动力学标定、
Wuji 驱动接入及实机验证。
