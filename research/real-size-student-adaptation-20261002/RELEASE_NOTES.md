先查看HTML内嵌两张照片与操作视频，做最小滑块肩部修形后，实际完成同父C3200的C/R各800次Adam更新（54400→55200）。R仅替换75%目标槽的几何/合法初态，25%旧四来源锚点相同；actor、teacher encoder、normalizer、SC-real2076输入、loss与controller不变。没有第二窗口。

独立32个来源3初态确认：R800 **K20 22/32、持稳26/32、有序开关28/32、S5 0/32**；父与同预算C800 K20均0/32。配对K20提升68.75个百分点，bootstrap95%区间[53.125,84.375]个百分点。R接近teacher开发集参考，但没有独立teacher可靠性认证。原尺寸小型保留K20三者16/16；S5父13/16、C14/16、R11/16，存在精度代价信号。

4个额外新诊断状态：零载荷2/4、0.05N阻力上限0/4、相同载荷加0.5mm位置偏置1/4；不能建立负载可靠性或按压收益。下一步优先保持支撑稳定的轴向推进与端点保持。

新增1600 Adam更新、1,638,400 transition；**0.744510 GPUh**，保守累计56.117988/64，剩余7.882012。实际4H200，所有本轮GPU作业正常退出。代码与证据包包含两臂54800/55200 checkpoint、原始轨迹、静态状态、配置/恢复身份、媒体与账本；旧冻结结果未改。配对视频是预登记同状态RTX相机重仿真，保留失败，非H200统计或真机。

证据包SHA256：0e60970a10ca47a4a01ca495c98798dbcae378efd352ece6a8afdfeb37ccb00b。实物主体尺寸已知，其余接触尺寸/行程/质量等仍为估计，不是真机标定。未变父权重复用[width v1](https://github.com/Jr-kelly/artgym/releases/tag/wuji-width-student-distillation-20261002-v1)。

[中文报告](https://github.com/Jr-kelly/artgym/blob/420d84d8e461fb23807c315b7d7ceb823b835bfb/research/real-size-student-adaptation-20261002/REPORT.md) · [复现/续接](https://github.com/Jr-kelly/artgym/blob/420d84d8e461fb23807c315b7d7ceb823b835bfb/research/real-size-student-adaptation-20261002/REPRODUCE.md)
