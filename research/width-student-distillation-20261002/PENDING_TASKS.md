# 当前剩余工作

2026-10-02 19:14北京时间：17314已恢复。服务端18:10杀停原因为四小时平均GPU利用率19.9461%<26%，不是认证失败。临时目录丢失，八个未完成final的原收据与保守1.4 GPUh记账保留。

冻结模型、源码、初态及batch均未变化；`queues/frozen-final-resume-v2.json`对8个中断任务使用唯一retry1目录，其余82项沿用原身份。90项最终评测正在8H200有限队列中执行，原始轨迹边完成边回传归档。

剩余：全部90项独立复算、最终能力/失败报告、15个最终raw分包与最终分析发布到final-v2 Release；复用v1已经公开的权重、训练/dev/confirmation及视频。禁止重新训练或因final结果更换候选。

监控：UTILIZATION_RESUME_MONITOR.json及UTILIZATION_RESUME_SAMPLES.jsonl。旧43.25%只覆盖109分钟；四小时利用率以官方杀停通知19.9461%为准。所有PID/状态再次接手时须复核。
