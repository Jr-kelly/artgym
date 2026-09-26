# G2＋Wuji 过夜实验视频索引

本轮没有连续两轮稳定伸缩成功。所有视频无文字、原速30fps、单次连续执行；近景来自该次运行的同步相机，没有跨运行拼接。A预置对照不属于真实获取。R3-16最终支持反馈结果见报告与原始轨迹。

| 文件 | 来源与时长 | 实际范围及限制 |
|---|---|---|
| [g2-wuji-table-pickup-one-cycle-unstable-thumb-ablation.mp4](https://github.com/Jr-kelly/artgym/releases/download/g2-wuji-overnight-20260926-v1/g2-wuji-table-pickup-one-cycle-unstable-thumb-ablation.mp4) | R3-14，96.967秒 | 正常桌面初态→取刀→翻掌→拇指离触/到滑块→仅拇指策略动作。后一轮开合、约42mm行程，但首轮及全程稳定失败，非原完整teacher成功 |
| [g2-wuji-same-run-hand-closeup-one-cycle-unstable-ablation.mp4](https://github.com/Jr-kelly/artgym/releases/download/g2-wuji-overnight-20260926-v1/g2-wuji-same-run-hand-closeup-one-cycle-unstable-ablation.mp4) | 同一R3-14，96.967秒 | 同步近景，便于看接触与刀身转动；不替代完整视角 |
| [g2-wuji-table-pickup-slider-contact-full-teacher-failure.mp4](https://github.com/Jr-kelly/artgym/releases/download/g2-wuji-overnight-20260926-v1/g2-wuji-table-pickup-slider-contact-full-teacher-failure.mp4) | R3-12，96.967秒 | 相同桌面前缀→滑块接触→完整冻结teacher，接管后0.167秒首次失滑块接触、0.667秒首次失稳 |
| [g2-wuji-table-pickup-thumb-release-support-failure.mp4](https://github.com/Jr-kelly/artgym/releases/download/g2-wuji-overnight-20260926-v1/g2-wuji-table-pickup-thumb-release-support-failure.mp4) | R3-10，65.300秒 | 桌面初态→翻掌→支撑重建→拇指退出时保持失败；原无名指预载未退 |
| [g2-wuji-thumb-release-support-failure-closeup.mp4](https://github.com/Jr-kelly/artgym/releases/download/g2-wuji-overnight-20260926-v1/g2-wuji-thumb-release-support-failure-closeup.mp4) | 同一R3-10，65.300秒 | 同步近景，展示支持交接失败 |
| [g2-wuji-A-preset-current-wrist-teacher-two-cycles.mp4](https://github.com/Jr-kelly/artgym/releases/download/g2-wuji-overnight-20260926-v1/g2-wuji-A-preset-current-wrist-teacher-two-cycles.mp4) | R3-15，22秒 | 独立预置A＋实际2秒停稳＋20秒teacher两轮成功；未执行取刀 |

全部开发原始轨迹、接触、配置及逐项源码恢复信息在增量证据包。非所选视频也保留于本机各原始试验目录，没有覆盖旧视频。SHA256SUMS与发布核验记录用于核对附件，代表视频帧数与原始轨迹帧数一致。
