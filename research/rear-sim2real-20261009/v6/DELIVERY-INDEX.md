# v6 文件交付入口

现有控制器与网络代码、bundle-deploy-v11和26项新增验证已在本分支。原策略、权重、参考和反馈补偿保留。没有训练、新物理仿真或完整矩阵重跑，真机结果仍未取得。

- [完整操作指南（公开脱敏版）](../FIRST-FIELD-SESSION.md)：启动、GDT/remote_env、初始化、摆刀、响应、probe、卸载复位、完整推动和结束。
- [实现与验证报告](REPORT.md)、[验证结果](VERIFICATION.json)、[包核验](PACKAGE-CHECK.json)。
- [当前自研部署包](delivery/rear-v6-deployment.tar.gz)、[恢复脚本](delivery/restore_wuji_rear_deployment.py)、[SHA256SUMS](delivery/SHA256SUMS)。
- [私有完整交付](https://github.com/Jr-kelly/artgym-wuji-private-delivery)：原现场指南、私有适配代码、实际依赖包、原摆刀材料和完整私有部署包；需要该仓库访问权限。

私有源码、内部资料、厂商包不进入公开ArtGym仓库。当前公开包仍为已验证的固定v6归档，其哈希与PACKAGE-CHECK一致；不因补交Git文档改写旧运行证据。
