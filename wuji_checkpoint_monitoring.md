# Wuji 训练巡检与自动评估

2026-09-21 已部署，每 300 秒检查一次：

- 本机 `runs/wuji_knife_fingertip_sapg`。
- 四卡机 `runs/wuji_knife_fingertip_4gpu`。
- 四卡机 `runs/wuji_demo_aligned_sapg`，已完成 1000 轮，继续归档结果，不自动追加训练预算。

监控训练进程、日志更新时间、当前轮次和新 checkpoint。超过 15 分钟没有训练日志、训练进程异常退出或评估失败，会记录到状态文件。

新发现的 checkpoint 在 CPU 上读取并提取独立的不可变策略快照，避免 `last/model.pth` 被覆盖或 checkpoint 清理影响评估。读取期间检测文件是否发生变化；不完整或变化中的文件留到下一次扫描重试。同一轮只评估一次，已有的原生评估直接复用。原生评估正在运行时等待它完成。缺少原生评估的保存点进入持久化队列，优先处理较新的权重，但不丢弃已排队的旧权重。

扫描与评估分开执行，长评估不会阻塞每 5 分钟的扫描。每台机器最多启动一个额外评估进程：本机共享 GPU 0；四卡机共享 GPU 1，原有原生评估仍使用 GPU 3。会占用部分算力，不中断训练。每个评估实例失败最多尝试 3 次。

多抓姿 teacher 沿用既有评估协议：几何 000、010、020 的 22 个 test 抓姿，每姿态 5 次，共 110 次，固定 seed、确定性策略、物理随机化开启。单抓姿对照重复训练抓姿 5 次、无随机化；该结果只衡量案例学习，不代表泛化。

## 状态与结果

本机总状态：

```bash
cat /data/research/artgym/runs/checkpoint-monitor/status.json
```

本机总状态的 `remote` 字段在每次 5 分钟巡检中更新，包含四卡机两个任务。时间戳使用 UTC。每个任务额外评估的最新结果：

```text
runs/<训练目录>/evaluation/monitor/latest.json
```

单次额外评估位于 `evaluation/monitor/epoch_NNNNNN/`，包含命令、日志和结果；原生评估仍保留在原位置。监控队列位于 `runs/checkpoint-monitor/jobs/`。

## 后台服务

本机由用户级 systemd 服务运行，已启用；服务异常退出自动重启。系统用户已开启 linger。查看服务：

```bash
systemctl --user status wuji-checkpoint-monitor.service
tail -f /data/research/artgym/runs/checkpoint-monitor/monitor.log
```

四卡开发容器没有可用的 systemd 用户服务或 cron，因此使用独立后台守护进程。本机每次巡检通过 SSH 确认它存活，若不存在则重新启动。SSH 断连不会停止远端扫描/评估；断连会在本机状态中记录，后续巡检自动重试。监控自动保存结果，不向聊天窗口、邮件或其他应用发送通知。

实现：`scripts/monitor_wuji_checkpoints.py`。部署配置：本机 `runs/checkpoint-monitor/config.json`，远端 `/home/wangjiarui/artgym/runs/checkpoint-monitor/config.json`。
