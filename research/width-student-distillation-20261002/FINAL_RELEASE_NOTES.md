本轮冻结最终评测已完成：90项任务、360个几何/来源/模型/协议单元，35,280条episode记录对应1960个独立初态。两组新优化随机流共12,800次真实Adam更新、13,107,200个新transition；第二组只作dev重复。完整源码、数据隔离与统计见[最终报告](https://github.com/Jr-kelly/artgym/blob/7b2af975ceadab90165c3e4c414ad62cbfca30f0/research/width-student-distillation-20261002/FINAL_REPORT.md)及[恢复命令](https://github.com/Jr-kelly/artgym/blob/7b2af975ceadab90165c3e4c414ad62cbfca30f0/research/width-student-distillation-20261002/REPRODUCE.md)。

| W120来源3：40秒开合且全程稳定 | P | C800 | G800 | C3200（冻结主候选） | G3200 | teacher |
|---|---:|---:|---:|---:|---:|---:|
| 联合成功 | 5/90 | 3/90 | 78/90 | 72/90 | 81/90 | 84/90 |

早期宽度覆盖有明显收益：G800在未见W115及W115+T110来源3分别54/59、49/54，P为3/59、4/54。但G3200的baseline来源1为50/128，P107/128，存在明显遗忘。G800的W120来源3 S2/S5严格到位均0/90，主C3200为13/90、3/90；不能把F成功等同于精密操作或全面保留。主候选在打开final前冻结，未因final重选。统计限于仿真合法初态附近扰动；没有真机/sim2real证明。

本版本25个资产：15个按几何/协议划分的原始轨迹包、最终独立分析与报告、98个成功/杀停作业收据、8张PNG/PDF统计/失稳图。每包服务器SHA256与本地清单一致；一个新轨迹包实际恢复验证42文件。**权重/Adam/RNG、训练、dev、confirmation及视频复用[v1](https://github.com/Jr-kelly/artgym/releases/tag/wuji-width-student-distillation-20261002-v1)，不覆盖旧版本。** [W120六模型视频](https://github.com/Jr-kelly/artgym/releases/download/wuji-width-student-distillation-20261002-v1/W120-six-model-comparison.mp4) · [baseline六模型视频](https://github.com/Jr-kelly/artgym/releases/download/wuji-width-student-distillation-20261002-v1/baseline-six-model-comparison.mp4)。视频为RTX4090/batch1单独重仿真，包含失败，不代替H200统计。

资源：本轮12.80505670 GPUh有实测作业时长，另保留8个杀停作业合计1.4 GPUh的保守timeout上界；历史40.43593222，累计保守记账54.64098892/64 GPUh，剩余9.35901108。2026-10-02 18:10北京时间，官方四小时平均19.9461%低于26%导致杀停。重连后临时目录丢失；仅8个未完成final各重试一次，源码/权重/初态/batch/阈值未变。所有GPU作业已退出，自建监控已停。局部采样均值不冒充四小时服务端指标。

下一步优先解决严格S2/S5到位精度保留；不盲目延长蒸馏、不重开本轮final调参。科学提交：`7b2af975ceadab90165c3e4c414ad62cbfca30f0`。
