# 当前 v6 恢复与验证

只使用一个当前rear-v6-deployment.tar.gz与已有已验证ArtGym基础，权重不重复分发。

```bash
python3 restore_wuji_rear_deployment.py --base "$ARTGYM_BASE" \
  --overlay rear-v6-deployment.tar.gz --destination "$DEPLOY_ROOT" \
  --bundle-path research/rear-sim2real-20261009/bundle-deploy-v11.json
```

恢复工具核验全部504项依赖。现场私有制造商扩展/包及完整FIRST-FIELD-SESSION.md单独交付；按该指南一次configure/setup后使用rear-field，不需要拼接历史版本。

本轮仅验证新增入口/模式/初始化/会话接续。既有20项合同、380帧对齐、1174周期全会话和假设10ms过渡的物理结果均复用，未训练、未重跑矩阵/物理。现场反馈映射、实际后处理、时钟、安装和停止需确认，real_robot_ran=false。

旧恢复/USB/状态server命令移至[历史](history/v3-v5-REPRODUCE.md)。
