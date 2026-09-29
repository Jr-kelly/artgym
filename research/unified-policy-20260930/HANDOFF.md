# 最新统一策略Goal：训练停止，失败候选冻结，最终验证运行（2026-09-29T17:30UTC）

继续同一原生Goal，不创建子代理。独立worktree `/data/research/artgym-experiments-20260921/unified-policy-20260930`，附件全文 `research/unified-policy-20260930/GOAL.md`。当前无进一步训练权限分支：两初始化+两有依据修正均未通过G2，按停止规则收尾，不再开第三方法、不根据最终集调参。最佳失败候选 `runs/unified-policy-20260930/bc-unified-historical-s3001-seg1/epoch_000100.pth`，SHA `3801eca359022e729510fef28f00d43b35af8561755f20a5f4be0206b6a07ab8`。完整排序和最终协议见 `final-freeze.json`。仅仿真已训练基础抓姿邻域；teacher未过，student/第二种子/D1/D2未触发。

实际17:28:33UTC启动最终评估：wrapperPID7769 GPU0固定2s，7770 GPU1固定5s，各timeout5500s，每来源128、batch512，五模型 historical/source3/single_historical/single_source3/unified 顺序同初态。目录 `runs/unified-policy-20260930/final-t2,t5`。必须重查PID与status，不重复启动。视频等待队列PID7940，`/tmp/wuji-unified-video-queue.py`，最多5800s等待，每个GPU对应final结束才用同GPU录制demo-t2/t5，各timeout1200s；初态固定开发rows[0,32,64,96]，不挑成功。视频用最终冻结同一权重，无source routing。H200若相机不可用，保留失败证据并在远端任务结束后本机4090独立重仿真；并发仍≤2GPU。

授权唯一主机 `wangjiarui@10.13.160.5:33024`，key `/home/agiuser/.ssh/id_ed25519_h200`。远端项目 `/tmp/artgym-unified-policy-20260930`，python `/tmp/wuji-unified-runtime/bin/python`；PYTHONPATH=.:rl_games LD_LIBRARY_PATH=/tmp/wuji-unified-runtime/lib TORCH_EXTENSIONS_DIR=/tmp/wuji-unified-torch-extensions。禁止使用旧日志主机；NAS runtime延迟大，不用于计算。只读monitorPID3901每5s全机4卡采样，结束须核验后停止。17:23资源快照1.332GPUh，历史采样覆盖~62min整机均值22.7%，不是四小时指标、不能宣称满足26%；最终双卡有用计算中目标>40%，不得填充无用任务。

预算开始09-29 15:56:50UTC，截止09-30 07:56:50UTC，训练截止06:26:50UTC，24GPUh/训练22GPUh/max2GPU，留90min/2GPUh收尾。目前远早于期限，但训练按失败分支已停止。

G0专家复核通过，G1扰动单专家克隆32+64通过。统一历史CP100 dev32 strict2=[32,32,32,1],5=[32,32,32,3]，body源3=29/30其余32。源3初始化CP100 strict2=[1,1,0,27],5=[0,0,0,30]。第一修改补偿换宽normalizer失败，第二修改历史原起点lr1e-4失败 strict2=[32,32,27,1],5=[26,32,32,2]；跨全部CP历史100按worstbody胜出。所有复算/report/gate在research；最终128现已开始，此后不得改模型。

新Release草稿 `wuji-unified-policy-20260930-v1` 已建，上传会话56007运行 `scripts.upload_wuji_unified_assets`，日志 `/tmp/wuji-upload-assets.log`，服务器digest逐项核验。当前只上传启动时已有10归档；normfix/lrfix/最终/视频后续需再上传。`delivery/unified-policy-20260930/`明确gitignore，大二进制只放Release。父专家和single-source3归档已解包SHA核验；CPU恢复BC100/101优化器/RNG通过，恢复训练100→101此前实际执行。新分支GitHub最后验证b3619d290afd5782ec42a307cbf49ada5c4731dd，还有待commit的后续代码/报告。普通push helper外部gitconfig权限失败，可靠方法：rsync common git(`/data/research/artgym-g2-tabletop-20260925/.git/`排除worktrees/index/logs)到`/tmp/wuji-unified-publish.git/`，bare push真实GitHub；不能force。

下一步：最终结果双实现复算；按冻结同权重渲染并用package_wuji_unified_video变四列、标teacher/独立演示/每格成功失败；报告逐来源Wilson及body，恢复命令、权重SHA、完整资源账本，打包实际lrfix/最终/视频。GitHub新commit和Release公开验证、下载哈希；核实计算和监控结束；最后回复明确统一未达标、teacher/student状态、唯一下一优先及链接。具体journal见DECISIONS.jsonl和实验根runs/wuji-goal/journal/events.jsonl。


2026-09-29T17:30:46.793964+00:00 release_asset_server_digest_verified {"name": "wuji-unified-pilots.tar.gz", "sha256": "e93c7921ebdb25e520169d9bf478af3600e19a06eb5ca18ad32692458d584a28", "release": "wuji-unified-policy-20260930-v1", "next": "Retain draft until final report/video/checkpoint decisions and public download verification"}

2026-09-29T17:30:47.481052+00:00 release_asset_upload_started {"name": "wuji-unified-single-historical.tar.gz", "sha256": "05282b91f75b97b451aeb4ebf6bf8fd3867a2e5564a3d7bb14f8c73cb7388291", "release": "wuji-unified-policy-20260930-v1", "next": "Verify server SHA256; do not overwrite existing assets"}

2026-09-29T17:30:57.267324+00:00 archive_started {"name": "wuji-unified-lrfix", "paths": ["runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1-dev-t2-wrapper.log", "runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1-dev-t5-cp100-job", "runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1-orchestration.json", "runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1-job", "runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1-dev-t5-cp50-job", "runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1", "runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1-dev-t2-job", "runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1-wrapper.log", "runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1-dev-t5-cp50", "runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1-dev-t2", "runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1-dev-t5-cp100-wrapper.log", "runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1-dev-t5-cp100", "runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1-segment-completed.json", "runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1-orchestration.log", "runs/unified-policy-20260930/bc-unified-lrfix-s3001-seg1-dev-t5-cp50-wrapper.log"], "next": "Pack stopped second correction and raw development traces"}

2026-09-29T17:31:09.095383+00:00 archive_completed {"name": "wuji-unified-lrfix", "archive": "delivery/unified-policy-20260930/wuji-unified-lrfix.tar.gz", "sha256": "31d681858d7265e4cab65f965479d204e295545cd7c6baf4d40c60f117d5c885", "size": 531959925, "files": 66, "next": "Upload immutable archive on next asset pass"}

2026-09-29T17:31:24.695547+00:00 release_asset_server_digest_verified {"name": "wuji-unified-single-historical.tar.gz", "sha256": "05282b91f75b97b451aeb4ebf6bf8fd3867a2e5564a3d7bb14f8c73cb7388291", "release": "wuji-unified-policy-20260930-v1", "next": "Retain draft until final report/video/checkpoint decisions and public download verification"}

2026-09-29T17:31:25.370531+00:00 release_asset_upload_started {"name": "wuji-unified-single-source3.tar.gz", "sha256": "3a8c712ba8d2a7a990e28e9f10d40201cd91bd623281f01f8c34edd68324a75e", "release": "wuji-unified-policy-20260930-v1", "next": "Verify server SHA256; do not overwrite existing assets"}

2026-09-29T17:31:52.437370+00:00 archive_started {"name": "wuji-unified-assets-and-resets", "paths": ["assets/hands/wuji_artbot", "assets/objects/knife_wuji_bridge3_20260922", "research/unified-policy-20260930/data", "research/multigrasp-20260928/data/small.npy"], "next": "Bundle exact physical assets and all frozen reset arrays; no changed physics"}

2026-09-29T17:31:52.588377+00:00 archive_completed {"name": "wuji-unified-assets-and-resets", "archive": "delivery/unified-policy-20260930/wuji-unified-assets-and-resets.tar.gz", "sha256": "52b44557ba0291d753c88274d8a0fd97e3a57ff0ab37a5a1ea34147d1d3991ce", "size": 4397137, "files": 82, "next": "Recovery manifest includes physical asset hashes; upload after ongoing batch"}

2026-09-29T17:32:14.856377+00:00 release_asset_server_digest_verified {"name": "wuji-unified-single-source3.tar.gz", "sha256": "3a8c712ba8d2a7a990e28e9f10d40201cd91bd623281f01f8c34edd68324a75e", "release": "wuji-unified-policy-20260930-v1", "next": "Retain draft until final report/video/checkpoint decisions and public download verification"}

2026-09-29T17:32:15.532590+00:00 release_asset_upload_started {"name": "wuji-unified-train-t2.tar.gz", "sha256": "835f368a2a820f2abce20b6b84bed18d753944f9a9ee3678c62e40915072fea0", "release": "wuji-unified-policy-20260930-v1", "next": "Verify server SHA256; do not overwrite existing assets"}

2026-09-29T17:32:48.347899+00:00 release_asset_server_digest_verified {"name": "wuji-unified-train-t2.tar.gz", "sha256": "835f368a2a820f2abce20b6b84bed18d753944f9a9ee3678c62e40915072fea0", "release": "wuji-unified-policy-20260930-v1", "next": "Retain draft until final report/video/checkpoint decisions and public download verification"}

2026-09-29T17:32:48.967150+00:00 release_asset_upload_started {"name": "wuji-unified-train-t5.tar.gz", "sha256": "a1b16a5127bca2234cdd9e04ff9fa20a17fffd06c76ac7ef3dae672ef2aac187", "release": "wuji-unified-policy-20260930-v1", "next": "Verify server SHA256; do not overwrite existing assets"}

2026-09-29T17:33:24.621730+00:00 release_asset_server_digest_verified {"name": "wuji-unified-train-t5.tar.gz", "sha256": "a1b16a5127bca2234cdd9e04ff9fa20a17fffd06c76ac7ef3dae672ef2aac187", "release": "wuji-unified-policy-20260930-v1", "next": "Retain draft until final report/video/checkpoint decisions and public download verification"}

2026-09-29T17:34:28.066728+00:00 资源分类更正：原bc前缀把BC开发评估误计training；按实际command划分offline_training/expert_collection/eval/demo，总GPUh未变。最终用resources脚本更新值，不引用旧training小计。
