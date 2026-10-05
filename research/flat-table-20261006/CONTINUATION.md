# 完整平放桌面取物续接
实际副本 /data/research/artgym-experiments-20260921/flat-table-20261006，分支 feat/wuji-flat-table-20261006。
读取 STATE.json、events.jsonl。原始附件仅本地，不发布私人媒体。旧contact-transfer成果完整保留。
本轮顺序：完整平放→机器人真实接触移位或侧夹→旧功能抓姿附近→不重置推动>20mm/保持1秒→局部泛化及冻结验证。
使用 scripts.record_wuji_flat_table_event.record 同步中央journal与handoff。禁止子代理。位姿接口允许sim_oracle，带误差时独立物理初态与估计。
用户本条利用率要求覆盖附件无最低利用率文字：有用GPU作业目标>40%，四小时26%；不能假报短窗达标。允许复用旧RL任务作为有用补充，保护其他进程。
环境 source runs/contact-transfer-20261006/env.sh。远端 ssh -p33024 wangjiarui@10.13.160.5，2026-10-05T18:17:47Z核实4×H200空闲，需重新核验。
当前动作：检查既有桌边握姿的接触几何，开发由完整桌面到边缘的物理前缀；不能瞬移刀或阶段重置。

2026-10-06本轮阶段收尾：先读FINAL-REPORT.md、results.json、REPRODUCE.md。14个开发物理试验无拾取成功；最佳新增是push-v5/pose-v5与corner-v10真实桌面推移、撤手、推后oracle位姿重新规划。视频在delivery/flat-table-20261006/report.html，全景与近景完整，未拼接。不要当成A→B完成，不启动冻结泛化重跑。
远端四组辅助旧桌边PPO67/66/68/66更新已停止，8个checkpoint和所有训练失败记录复制到remote-auxiliary-records；0完整成功，不推广。旧actor哈希保持6e89a2...。资源最终短窗47.87%/910.8秒，不能称四小时达标。所有本轮计算与monitor均需接手时再核实。
下一条有依据路线：部分折起ring/pinky避开桌子，以index/middle/thumb先抬升，再真实换握到旧操作承托；先做几何可执行路径与一次连续短连接。禁止重复低指垫/过推距离/旧桌边PPO支线。真实视觉和硬件未验证，goal仍未解决。
