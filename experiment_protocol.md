# Eight-H100 experiment suite

Current scheduling at 2026-09-22 05:13 CST: the three Sharpa arms remain on
0/1, 2/3 and 6/7. Multi-grasp pose-cost teachers occupy 4/5 and finish at 150
epochs; the two official-actuator continuations then restore full CP25 there.
Those new continuations have not yet started. Two extra low-gain teachers were
deliberately stopped on 6/7 after preserving CP25 when sharing slowed Sharpa;
Sharpa recovered to about 32 seconds/update. Historical allocation notes below
are retained. The current four-card suite separately runs the official-actuator
timed-command pair, with a 33-training/5-validation precision continuation queued.
Exact settings, actual preflight states, static-grasp failures and independent
evaluation counts are recorded in the 05:13 section of wuji_goal_progress.md.

Host: `ssh -p 30147 wangjiarui@10.14.0.106`.
Remote root: `/home/wangjiarui/artgym-experiments-20260921`.
Local source: `/data/research/artgym-experiments-20260921`.
The previous `/home/wangjiarui/artgym` and local 4090 runs are separate baselines.

## Allocation and dependencies

| GPUs for training | Run | Purpose |
|---|---|---|
| 0,1 | `sharpa_paper_reference` | Original Sharpa left hand, official assets/grasps, paper equations and explicit paper protocol |
| 2,3 | `sharpa_reward_corrected` | Upstream reward/timing, correcting only target-switch bookkeeping and fallen/invalid success credit |
| 6,7 | `sharpa_reward_upstream` | Matched control for the preceding arm; same data, seed, batches and timing, original reward |
| 4 (completed; now data) | `wuji_single_upstream` | Known-feasible demo initial grasp and physics, original reward |
| 5 (completed; now data) | `wuji_single_corrected` | Same Wuji conditions with only reward correction; no action/trajectory imitation |

Scheduling was revised after the provider terminated the eight-H100 instance at 16:20 on 2026-09-21 for 25.2853% mean GPU utilization over four hours (minimum 26%). All 30 Sharpa training geometries were already complete, but the old scheduler unnecessarily waited for the last held-out geometry before starting RL. That dependency is removed: all three Sharpa arms start after `sharpa-train-ready.json` confirms 30 complete training objects; evaluation separately waits for `sharpa-ready.json` to confirm all five held-out objects. Checkpoints accumulate in the durable queue during that wait.

Sharpa and Wuji data jobs now share one work queue. One remaining Sharpa object cannot prevent the other GPUs from generating Wuji data. GPUs 4–5 serve data jobs after the completed single-grasp experiments; GPUs 0–3 and 6–7 may each also host one generator alongside training once every training preflight has passed, with at least 60,000 MiB free before launch. Scheduling settings reload without restarting teachers. This changes scheduling only; the paper arm's environment counts, minibatches, reward, controller, physics and sample budget are unchanged. Every production object still requires 1,000 candidates and physical validation.

The initial 24 GB admission threshold underestimated Wuji generation's memory peak. Native contact projection failed on Wuji 002, 003, 005 and 011 while sharing a GPU with training; those attempts and their unsaved-candidate counts are archived under `runs/experiment-suite/interrupted/20260921T1906-oom/`. The native CUDA extension allocates workspace outside the PyTorch allocator. New Wuji jobs split only its independent projection queries into chunks of 128 and release unused PyTorch cache above 2 GiB. Candidate sampling batches, RNG, IK iterations, and filtering thresholds are unchanged. `scripts/check_projection_chunking.py` compared original/chunked outputs on both real hand meshes, 259 candidates, five contacts, two orientation weights and both output frames: all eight cases were finite and bitwise equal (maximum absolute error 0). The audit is `runs/experiment-suite/projection-chunking-audit.json`. Failed attempts restart with their original seeds; existing completed datasets are retained. Sharpa generation continues through the original projection call.

The private generator runtime was restored from its verified archive after the resource restart. The unfinished Sharpa 030 attempt is archived under `runs/experiment-suite/interrupted/20260921T1620/`; its 676 candidates had not been written by the official entry point, so generation restarted with the same seed. Completed datasets and checkpoints are retained. Recovery checkpoints retain policy/optimizer state and counters; the upstream environment does not serialize the full simulator state, so a training restart is not an exact continuation of the previous physical trajectory.

`monitor_gpu_utilization.py` samples all eight GPUs every 10 seconds and publishes one-, five-, fifteen-minute and four-hour averages to `runs/gpu-utilization/status.json`. The operational target is 40%; an alert appears if the available fifteen-minute window averages below 35% after five minutes of samples. Windows explicitly report their observed duration; they do not claim four hours of evidence after a restart. These local samples approximate the provider's accounting. The local watchdog checks status and records utilization every minute.

After both 35-object datasets completed (Sharpa 19:30, Wuji 19:45 CST), evaluation moved to the idle GPUs 4 and 5 with at most one worker on each. The previously launched GPU-7 worker drains without interruption. The durable queue uses oldest-discovered-first ordering so slow training arms receive evaluations promptly. This changes scheduling only. Earlier GPU-7 evaluation contended with the upstream teacher pair and coincided with 400-second update phases; throughput after draining is checked separately. The legacy local/four-GPU monitors retain their single-worker default.

## Reference protocol

Official revisions: ArtGym `63b94fb3364596db51b7e4651b3c3c98ff994710`, make_data `eafa7b6e84811de211757119081f86b3f236495f`, func_lygra `55f60c7e8f8db2ab55b50f6af5a07efcad191f57`.

Each Sharpa arm uses 20,000 total environments, two ranks of 10,000, horizon 16, 320,000 global transitions/update, 6,250 updates = 2B transitions. The implementation interprets the paper's 40,000 minibatch and 4,000 exploration-group size as **global**: 20,000 minibatch and 2,000 environments/group per rank. Five exploration levels are repeated across ranks. This distributed interpretation is declared because the paper does not specify the rank mapping.

Shared: 120 Hz simulation / 30 Hz control, alpha = 0.025 rad/action, LR 0.0002, adaptive schedule, gamma .998, GAE .95, published SAPG architecture, stability curriculum epoch 100 to 1100. Object mass/friction/damping ranges follow Table 8. Knife dimensions use official Table-6 batch config. Objects 000–029 train; 030–034 held out. Each gets 1,000 official generated candidates followed by the original one-second ArtGrasp filter (five contacts; .05 m/1.57 rad thresholds). No failed object can silently be dropped from training.

The upstream within-instance 80/20 grasp split is retained for training; it is separate from the 30/5 geometry split. Evaluation deduplicates the complete physically valid pool using object translation <=5 mm, quaternion angle <=.05 rad, AND hand-joint RMS <=5 degrees. The paper requires pose and hand deduplication but does not publish numeric thresholds; the pose thresholds come from the public validator, and the joint threshold is an explicit assumption. Original candidate and validated arrays are preserved; retained indices are recorded in each `valid/deduplication.json`.

`sharpa_paper_reference` uses the Table-7 normalized-action difference and physical base velocity, corrected per-stage progress accounting, immediate distance-based success switching, and a 1,200-control-step horizon without the undocumented 10-second stage timeout or random dwell. Success on a fallen/invalid transition is excluded. The paper does not define simultaneous success/drop ordering; that choice is explicit here.

The two `sharpa_reward_*` controls preserve upstream target-difference smoothing, finite-difference velocity/clipping, dwell (0–2 s training/1.5 s evaluation), 10-second stage timeout and success-event bonus. They share the paper action/batch/curriculum parameters. Their sole experimental difference is reward bookkeeping/drop-success masking. They must not be labeled exact paper-equation runs.

External random forces are disabled in these reference arms because they are not specified in the paper's randomization table. H100 hardware and the existing multi-GPU compatibility changes differ from the reported RTX 5090 setup. This is a documented reproduction protocol, not a claim that unknown author details have been recovered.

## Wuji stages

The first pair each uses 2,560 environments for 2,500 updates = 102.4M transitions, with identical seed, initial grasp, absolute 120 Hz hand control, low slider damping .3, and no domain randomization. Both retain all 20 learned hand actions. They compare the reward fix in isolation and do not establish category generalization.

Separately, official make_data generates 35 realistic slim knives; func_lygra uses official knife contact labels with an explicit ArtBot robot-name/link/frame adapter. These new caches remain isolated from the existing locally generated dataset. This adapter must be validated before using the data for transfer training.

Expansion to paper-style relative control, multiple grasps, then multiple objects requires a successful learned single-case evaluation. A failed acquisition run does not automatically trigger more expensive category training. Real hardware calibration and grasp placement remain outstanding.

## Checkpoints and evaluation

Short checks run three updates at the requested environment count and GPU count, then verify checkpoint epoch/world size before a fresh formal run starts. Three updates check execution and checkpoint integrity; they do not demonstrate learning. The corrected Wuji physical reference must first pass in all 32 environments.

Sharpa: first checkpoint at epoch 10, then every 50; keep six recent recovery checkpoints and every 500-epoch milestone. Wuji: first at 10, then every 25; keep six recent and every 250-epoch milestone. Each scheduled checkpoint publishes a separate immutable policy snapshot; the five-minute monitor queues each snapshot, with no intentional skipping. Best/earlier policies remain available through those snapshots.

Sharpa periodic evaluation: all deduplicated valid grasps of all five held-out geometries, ten randomized rollouts/grasp, 10 mm tolerance. Final checkpoints use 100 randomized rollouts/grasp. Wuji periodic evaluation: the single training grasp, five repeats, 5 mm tolerance. Both Wuji policies are evaluated using the corrected success/drop accounting. The monitor now computes Section 4.1 IC, GC, CSC_mean, CSC_max and execution-level SR from saved per-grasp trial matrices. Coverage/CSC weight instances equally; SR weights executions equally. Failed instances contribute zero CSC, an explicit convention where the paper's successful subset is empty. Do not equate reward increases or reference replay success with learned success.

## Verified startup evidence

- `runs/experiment-suite/unit-tests.log` and `reward-tests-final.log`: 18 distinct passing reward, checkpoint and evaluation-metric tests; the final reward check includes the paper evaluator's disabled stage timeout.
- `runs/experiment-suite/wuji-replay/report.json`: reference motion completes a cycle in 32/32 simulated environments; this is not a learned-policy result.
- `runs/experiment-suite/sharpa-generation-preflight.json`: 16 official candidates, 3 physically valid grasps, with original collision checks retained.
- `runs/experiment-suite/sharpa-checkpoint-audit.json`: 2 x 10,000 environments, 3 updates / 960,000 transitions; finite and identical model/optimizer states across ranks, distinct rollout observations. This uses one geometry; full formal runs repeat their checks with all 30 training geometries.
- `runs/experiment-suite/full-dataset-preflight-audit.json`: all three Sharpa arms passed the full 30-geometry, 1,432-training-grasp, two-rank preflight with finite synchronized model/optimizer states and distinct rank observations. Each formal teacher is now running with the same full dataset.
- `runs/experiment-suite/sharpa-evaluation-preflight.json`: checkpoint loading, randomized full-horizon evaluation and per-grasp trial output verified. The untrained three-update policy scores 0/6 complete cycles; this check demonstrates evaluator execution only.
- `runs/experiment-suite/data/knife_wuji_official/000/status.json`: first 1,000-candidate Wuji job produced 15 physically valid grasps.

The first capacity check failed because the temporary asset symlink resolved to a different cache name; the second lacked the bounding-box manifest. Both setup failures are retained under `runs/sharpa_capacity_smoke*`. The third completed without reducing the requested environment count. The public evaluator initially rejected the paper protocol's zero stage timeout; it now accepts zero specifically for that protocol, retaining the 1,200-step episode limit. An earlier contact-cache wrapper accidentally defeated the official resampling path; that wrapper was corrected and the zero-result attempt archived. Independent FK matched urdfpy within 1.3e-7; sampled IK position residuals were <=3.6 mm. The collision filter was not relaxed to obtain Sharpa results.

Generation runs in the private Python 3.10 environment `/tmp/artgym-lygra-runtime`, with its complete archive and checksum under `runtimes/`. `ensure_lygra_runtime.py` restores that archive if the node-local directory disappears. Simulation uses the existing Python 3.8 runtime without modifying its packages; `PYTHONPATH` explicitly selects this isolated checkout. The one-minute local watchdog restarts a missing remote coordinator; failed experiments remain visible and are not silently restarted with different settings.

The local 4090 host rebooted at 11:17 on 2026-09-21. Its interrupted baseline was resumed from full epoch-5800 state (including optimizer) under `/data/research/artgym/runs/wuji_knife_fingertip_resume_20260921`, with the original command parameters. Both old and resumed runs remain in the old monitor. On 2026-09-22 00:25 CST, the old four-GPU baseline was intentionally stopped after preserving CP5450 (892,928,000 transitions), following more than 100 evaluations without a complete cycle. Its source, checkpoints and evaluations remain intact; allocation records are under `runs/wuji-goal/archived-four-baseline`. The local baseline continues.

## Goal experiments, 2026-09-22

The user authorized independent training attempts on both remote hosts until a learned Wuji policy succeeds. The first controlled acquisition pair on the four-H100 host is defined in `wuji_acquisition_suite.json`. GPU 0 trains thumb-only control with the other sixteen support targets fixed; GPU 2 trains all twenty outputs, with support targets bounded to initial +/-0.04 rad and thumb targets incremented by up to 0.025 rad per control step. Both use 120 Hz physics / 30 Hz control, 2,560 environments, horizon/sequence length 32, five SAPG exploration groups, zero mean initialization and initial log standard deviation -1. They use the same realistic 147 x 19 x 11 mm, 35 g knife and one prescribed grasp, with free object base, passive slider damping 0.3 and no domain randomization. These physics are uncalibrated acquisition conditions.

The new reward keeps progress (1000), near-goal (1), smoothness (-1) and stage-success (50) terms; position/rotation stability penalties are fixed at -0.5/-0.02, missing-contact penalty is zero, drop costs -25 and each valid step adds 0.1. The new reward and action-space changes are a joint intervention; this pair alone does not isolate a single causal factor. It is explicitly separate from the paper-reference experiments. The policy receives no trajectory, waypoint, time index, expert-action label or imitation loss.

The new action mapping passed three CPU boundary/inverse checks plus both three-update simulator preflights. The known successful trajectory was feasible under the new control interface in 64/64 environments. That feasibility result is separately labeled scripted. Scheduled RL snapshots remain immutable: first CP10, then every 50 updates, six recent full recovery states plus 500-update milestones. GPU 3 evaluates each scheduled checkpoint every five-minute scan; GPU 1 performs independent physical audits. A local one-minute systemd watchdog ensures the four-GPU coordinator is alive. Utilization records are isolated from the shared-filesystem eight-GPU monitor (`runs/gpu-utilization-four`).

The all-twenty policy CP10 (819,200 transitions; SHA256 `883de1e59fdb383ac47faa540e2fd17a6e5e9b5ae7564e5bbcaa6ffa6a7ba48d`) passed 32/32 initial evaluations, 100/100 fresh-seed official evaluations, and a further 100/100 independently instrumented evaluations. The last group also passed a stricter first-cycle stability criterion of <10 mm base displacement and <0.25 rad base rotation; observed worst values were 1.773 mm and 0.1655 rad. A separate local 4090 rollout recorded a text-free learned-policy video and passed. The evaluation's open/close goals are 40/0 mm, with 5 mm tolerance and zero dwell. Success therefore does not mean exact endpoint contact. These trials repeat one initial grasp; they do not establish grasp or geometry generalization. Later perturbation/damping/tolerance tests are recorded separately.

Detailed evidence and remaining hypotheses are in `wuji_goal_progress.md`. The formal Sharpa arms continue with unchanged configurations. At approximately epoch 455 the paper-equation arm has collapsed to 6.54 control steps/episode, while the corrected-upstream arm at epoch 577 averages 584.8 steps and 5.93 completed stages. The smoothness and velocity equations differ across these arms; attributing the entire gap to reward bookkeeping would be incorrect.

After the single-grasp gate passed, allocation advanced: four-GPU 0 trains `wuji_acq_precision_ft_v1` (2 mm tolerance and 0.3 s dwell), GPU 1 trains `wuji_acq_fingertip000_ft_v2` (33 previously validated and direction-approved training grasps, five held-out grasps of the same geometry), GPU 2 continues `wuji_acq_all20_v1`, and GPU 3 evaluates the checkpoint queue. Both new runs passed three-update preflight and are in formal training. They initialize only model/normalization weights from CP10; each uses 5,120 environments, horizon 32, 1,000 updates, with fresh optimizers/counters. Learning rates are 0.00005 and 0.0001 respectively.

The thumb-only run was intentionally stopped after durable CP100; its CP50 evaluated 0/32, while the all20 CP50 passed 32/32. An attempted transfer to the new official object-000 dataset was stopped when all 12 training grasps failed the user's thumbwards direction requirement. Its record is retained. A complete official-data posture screen found 294/1,660 states within the approved pose envelope; these still need reach/contact screening. The running 33-grasp experiment uses the previous Wuji-specific fingertip dataset, not this new official dataset. Its v1 preflight hit the original 30-geometry guard. v2 explicitly names and validates a training-geometry subset; the original paper guard remains in force for paper runs. Source identity, output hashes, pose bounds and prior physical-validation thresholds are checked before the migration subset loads.

## Inspect

```bash
cd /home/wangjiarui/artgym-experiments-20260921
cat runs/experiment-suite/status.json
cat runs/checkpoint-monitor/status.json
cat runs/gpu-utilization/status.json
tail -n 25 runs/sharpa_paper_reference/teacher.log
```

Every generated object has `runs/experiment-suite/data/<dataset>/<id>/status.json`, its exact commands, generation/validation logs, output hash and grasp counts. Source/config and generated-asset hashes are retained. Dataset or training failures stop the affected dependency chain and appear in suite status; they do not silently fall back to the old data or alter settings.


### 2026-09-22 01:20 扩展与资源调整

Wuji 精细控制 CP10 已通过 100 次新种子独立物理审计（2 mm /0.3 s）；单抓姿源实验保留到 CP150 后主动释放 GPU0。CP100 的退化由额外 100 次轨迹定位为到位振荡、连续停留失败，96/100 打开超时，不能用训练回报替代任务成功。详细证据、未完成事项见 `wuji_goal_progress.md`。

官方 Wuji 35 几何严格迁移筛选完成，1660 个物理有效输入最终保留 200：训练姿态 143、训练几何上验证姿态 38、未见几何姿态 19。三几何 teacher 采用 001/002/003，27 train /9 validation，5120 环境、horizon32，500 轮（81.92M transition）预算。原始 URDF 通过相对符号链接复用，逐次核验物理筛选哈希与原始 train/test 身份。该迁移实验不声称覆盖全部 35 几何；000/007 筛选为空。原 Sharpa 三组参数与数据划分保持。

四卡分配：GPU0 三几何 teacher；GPU1 单几何多抓姿 teacher；GPU2 官方 student 蒸馏及其串行评估；GPU3 teacher checkpoint 评估。新 student 用精细控制 CP10，1024 环境，500 updates ×16 rolloutsteps，共8.192M transition预算。所有 CP 独立测试，初期零成功如实保留。评估和回归轨迹使用额外有界任务，结束即释放。

部署一致性只验证 CPU 观测/控制适配器与模拟器的数值语义，未涉及真实机器人或网络时延验证。源码根目录路径经重新核查无错，修复集中于配置继承、关节排列、动作协议和指令目标/实测角的区分；不修改原有正确的路径层级。


01:28补充：student CP100独立物理审计99/100至少一次完整开合，99/100首次循环满足10 mm/0.25 rad稳定性约束；本机无文字视频20秒4次。仍限定单初始抓姿、无DR，模拟器用物体状态进行成功判定和目标切换。该结果未覆盖真机或自主目标阶段检测。模型对已单独冻结，后续CP继续评估；验证抓姿0/2及初始扰动对照已列入有限诊断队列。

### 2026-09-22 01:54 成对扰动实验与抓姿分布诊断

八卡新增精细teacher继续训练与初始扰动两组，分别在GPU5/4，与Sharpa周期评估共享。两组从同一已验证精细CP10仅加载网络/归一化统计，新优化器；5120环境、32步horizon、300轮、LR5e-5、种子20260929。前100轮把扰动从零升至位置每轴0.5 mm、关节0.01 rad、旋转向量每轴0.5°。配置、预检、正式命令与五分钟评估保存在`experiment_suite.json`及`wuji_augmentation_monitor.json`。到第23轮已从训练事件文件确认扰动比例0.23。原三组Sharpa参数、数据划分不变。

小扰动独立审计：student CP100为64/100成功、61/100首次循环稳定；CP125为62/100和58/100，虽然CP125名义初始化100/100。这些还不是新几何泛化。teacher对同一扰动集合的审计用于判断teacher与蒸馏各自的局限。

验证姿态0/2及精确接触对诊断发现运动学可达与动态接触稳定性存在差距，详见`wuji_goal_progress.md`。没有放宽筛选、删除失败验证样本或把验证姿态加入训练。33个训练姿态只含1个明显弯曲拇指末端的类别；已准备训练池两类各50%采样的单因素干预。分组由训练数据最大关节间隔产生，保留源行身份与哈希，未读取验证数据来计算权重。该诊断先检查所有训练姿态，再决定是否启动正式对照。

02:05结论：CP100训练集119/132，少数形态训练行29为4/4，故未启动采样干预；候选实现归档，活动任务恢复。精细teacher同一100个扰动状态为63/100（严格60/100），teacher自身也有明显初始化误差问题。新增有限的CP50至CP300成对扰动审计；随机扰动课程和未扰动控制均已通过CP10名义32/32评估。

新连续开合成对实验定义于`wuji_acquisition_suite.json`，两组均从多抓姿CP100、只加载模型/归一化统计，5120环境、horizon32、300轮、LR5e-5、种子20260930。只改变`maxConsecutiveSuccesses`：0（训练至20秒/超时/掉落）或2（完成一个循环后重置）。两组保留全部33 train/5 validation，均通过3轮预检。四卡GPU2/3分别训练，与剩余student评估和串行teacher评估共享；新监视器`wuji_multicycle_monitor.json`独立保存日志与指标，不中断旧评估。Student500次更新已正常结束，CP500评估仍须完成。

02:18结果补充：扰动组CP50完整扰动19/100（严格17），无扰动对照CP50为57/100（严格57），原精细CP10为63/100（严格60）；增强收益未获支持。扰动CP50名义block0为0/32，随机动作诊断5/32（严格0），五个block确定性各0/32，均保留失败。连续开合CP10与重置对照的首次SR分别29/50、34/50，均值循环3.44、1.28，报告权衡而非只取有利指标。训练行29宽松任务32/32，但0/32满足0.25 rad首次旋转门槛，动作质量不能由任务SR替代。Student20份周期CP评估已全部完成；CP500名义100次额外审计通过，扰动审计仍单独记录。

### 2026-09-22 02:40 单因素接近目标奖励对照

新的`wuji_acq_precision_near01_v1`与`wuji_acq_precision_near1_v1`在八卡GPU0/1上与原参考实验共享，均通过三轮预检。两组从精细CP10相同模型/归一化统计开始、新优化器，5120环境、horizon32、150轮、LR5e-5、种子20261002，均使用原初始扰动课程和2 mm/0.3秒要求。仅GoalDistance2权重为0.1或1，CP10及每25轮保存；名义独立评估和CP50/100/150的100次匹配扰动审计分开记录。原Sharpa任务配置、原始训练/验证划分未改变。

实验动机是固定轨迹奖励比较：成功精细CP10的首次循环折扣回报186.014，旧退化CP100为190.416；将接近目标项权重在固定轨迹上改为0.1后分别173.598/75.339。该反事实不含策略响应或重置后未来回报，不作为因果结论。完整证据和归一化交换反例见`wuji_goal_progress.md`。

新的冻结策略核查区分首次试验与所有已结束回合，防止不同回合时长改变统计权重；网络与归一化统计逐项未变。新多抓姿轨迹审计增加全程稳定指标：连续开合CP50为114/160完成、32/160首次稳定、0/160全20秒稳定。五格本机视频保留所有原始验证姿态和失败，已上传Release；它不满足最终稳健操作门槛。


### 2026-09-22 02:55 routine quality metrics and queued absolute-pose pair

Acquisition periodic evaluators now add an observer-only pose-quality protocol (strict <10 mm/<0.25 rad, complete first cycle, and separately survive the full rollout without fall/invalid). Old snapshots without these metrics are not silently ranked as stable. The full CP50 trace cross-check matches all per-trial maxima. A current160-environment evaluation validates integration. Formal Sharpa command lines and task behavior remain unchanged.

The absolute-pose pair `wuji_acq_pose_cost1_v2`/`wuji_acq_pose_cost0_v2` is queued behind both near-goal reward runs on GPUs0/1. It starts from multicycleCP100 SHA52a7ccf3837ce0434edab956b640167eeac24df10ea44fa489c38c19fcc11028, same33/5grasps,5120env,horizon32,150updates,LR5e-5,seed20261003,newoptimizer. A coefficient1 vs0 compares the bounded squared normalized absolute position/rotation error with a50-update ramp. All other task/reward/control settings remain. Both launch layers enforce dependencies. The accidentally early v1 preflights were stopped before teacher launch and remain recorded; no v1 result is used. Three-epoch actual preflights remain required before v2 teachers.


03:03 results: the streaming quality observer matches all per-environment extrema from the independent multicycleCP100 audit. At100matchedupdates, continuous training scores128/160complete,59strict,0full-stable; one-cycle-reset control90/32/0. Near-goal weight0.1 vs1.0 atCP50 scores68/66/33 vs24/21/7 per100identical perturbations; sourceCP10 is63/60/26. These are development results under one training seed per arm, not final unseen-geometry or hardware validation. The perturbation vectors are exactly identical. Failures of the low-weight arm are now chiefly closing after a successful open (23/100), plus insufficient open dwell (9/100). Both nominal variants remain32/32first-cycle successes.


### 2026-09-22 03:30 updates

Precisionnear01CP100 passes100/100complete+strictfirst on developmentseed1616 and each freshseed3179/4207, with full20s stability37/43/42 per100. The same-start weight1.0controlCP100 is14/11/1 onseed1616. All tests still perturb one prescribed grasp and do not establish broader geometry/grasp or hardware generalization.

Continuous33grasptrainingCP250 first reaches160/160completion acrossall5validationgrasps,includinggrasp2(32/32complete,19strict). Aggregate51/160strict and0fullstable remain insufficient. The unlaunched multigrasp pose-costv2pair therefore uses thisCP250 forbotharms, now onGPU4/5afterbothoriginalaugmentationarmsfinish. The separateprecisioncontinuouspose-costpair startsfromprecisionnear01CP100onfour-GPU0/2onlyafterofficial3andmulticyclefinish. Bothpairskeep150updates,5120envs,horizon32,LR5e-5 and comparecost1vs0; tasks retain their separate5mm/zero-dwell versus2mm/.3s criteria.

An optional batchpropertyreader (defaultfalse) matches originalmass/friction/damping/stiffness tensorsbitwise in1000realenvs without changing RNG orphysicalproperties. A separatefull20kenvdualrankCP600->603probe exits0 and passesmodel/optimizer/normalizersynchronization andresume-countersaudit. Itdoesnotreplaceformalreferenceorproveidenticaluninterruptedtrajectories. Formalreference GPUs0/1willbereleasedbyendingnear-goalruns;queuedposepairuses4/5instead.


CP125nominalprecisionfull-rolloutstability31/32triggeredapriority100trialperturbationaudit. The unlaunchedprecisionposecostpairmustbereviewedifCP125/150alreadyresolvessustainedprecisiontoavoidredundantexperiments. Physicalauditsnowalsosavetheirlaunch-timesourcebytes;priorCP100/video/interventionexecutedversionsarereconstructedandmatchedtothealreadyrecordedSHA256values.

### 2026-09-22 03:45 precision CP125 selection and student pilot

Both near-goal reward arms completed their fixed 150-epoch budgets with observed exit0. The low-weight CP125 was selected using development seed1616 (100 complete/100 strict-first/50 full20s per100), before two new seeds6259/7307 were tested. Those independent perturbation seeds produced200/200 strict first cycles and106/200 full20s stability. This remains one prescribed grasp/geometry; the full task and pose thresholds are unchanged.

Before either precision continuous-pose arm started, both sources were changed fromCP100 to the same CP125 SHA85ba4a542b7b9c06ff03a288eb2749d1ab061a5787270f9d6ac8cf568fc6aa15. A100-update student pilot on four-hostGPU2 is an additional scheduling dependency for both arms. Their coefficient1/0 comparison,5120envs,horizon32,150epochs,LR5e-5,training seed20261004 remain fixed. The finite perturbation queue evaluates bothCP50/100/150 on development seed1616; final independent seeds are selected only after choosing a policy.

The student pilot uses1024envs,100updates,16steps/update,LR1e-4,MSE+0.1cosine,seed20261005,deterministic actions,continuous20s and full reset perturbations. Unlike RL, distillation does not advance the task's RL epoch; its explicit reset-noise ramp is therefore0. Actual3-update preflight verified1024distinct initial targets,noise scale1.0,frozen actor/normalizers and teacher encoder unchanged,finite student,exit0. This is a student training change, not a retrospective claim about old student robustness. CP25/50/75/100 are retained for independent physical tests; latent loss and training rewards do not select a deployment policy. The first audit's incorrect task identity was rejected before rollout and is preserved; corrected v2 jobs use the actual task identity.

At03:57 the precision continuous-pose pair had passed both real preflights and entered formal training. Student pilotCP25/50/75/100 scored complete/strict/full per100 as9/7/5,8/6/2,43/41/6,75/74/37. CP100 was selected using the declared full-first/strict-first/completion priority before new seeds8147/9257 were launched. A400-update continuation restores only that student encoder with fresh Adam, keeps teacherCP125 frozen, uses seed20261006 and otherwise the same student task/settings. It shares four-hostGPU2 with the precision cost0 teacher; serialized finite audits useGPU1. This changes wall-clock allocation, not either teacher's batch/sample budget. CPU observation construction and the deployment policy/action path passed650simulated steps including1reset; no hardware or latency claim.


### 2026-09-22 04:24 updates: holding, coordinate and gains audits

Continuous precision cost1/cost0 CP25 score100/100strict-first and78/77full20s on matched development states. The shared continuous-training change is not isolated by comparison to the original teacher. Selectedcost1CP25 fresh seeds10103/11213 score200/200strict-first and142/200full20s. PilotstudentCP100 fresh8147/9257 scores173complete/172strict/100full per200.

New fixed-time20s audits alternate targets every2s/5s, suppress internalarrival switching, and independently measure each-window dwell, final0.3s endpoint dwell, and fullbase stability. ContinuousCP25 all-endpoint+fullstable success is10/100at2s and16/100at5s, so holding remains a gap. The queued same-source100epochhold2s-vs0.3spair changes onlytrainingdwell; uses5120env,horizon32,LR5e-5,seed20261007,posecost1andfullresetnoise. StartsafterfourhostGPU3multicyclecontrolandGPU0cost1respectively; eachrequiresreal3epochpreflight. Formal training still usesarrival-switching. CP25/50/100fixed-timeaudits forbotharms areprimary scores; no new pose/geometry/hardwareclaim.

Five-grasp2mm/.3s evaluation scores1/160for multicycleCP250 and0/160for single-graspcontinuousCP25. The explicit original-to-acquisition knife observation-frameadapter does not rescue this(0/160), and doesnot changephysicalgeometry orgrasps. All5validationrows remainheldout.

A pinnedofficialWujiMJCF mapping matchesall20jointaxes/limits/effort, maxlocalframedifferences.2001mm/.0007565rad; officialpositiongains0.18–0.69versuscurrent100 aretestedonlyasaseparate sensitivity. SameArtBotPhysXassetandCP25,100savedstatescompare100/1,10/.1,officialgains,andofficialgains+armature; officialMuJoCo geometry/solver are not copied. SDK effortlimit usescurrent-space A, not simulationNm; noSDK/hardwareaction performed. PaperC.5calibrationprocedure remainsunverifiedforWuji.

Monitor native-result reuse now still materializes immutable policy snapshots; olderalreadyrecordedjobs recovermissing snapshots onscan. NewfinitefuturequeuesreadcommittedtrainingCPs. No trainingrewardorphysics changedbythisschedulingfix. SixcontinuousCP25Releaseassets,includinguncuttext-free3trialvideoandfailure-awarefigures,uploadedandGitHubdigestsverified.


04:36 official-actuator transfer pair submitted: 100epochs each on eight-hostGPU6/7 alongside originalupstreamSharpa. SamecontinuousCP25, newoptimizer, seed20261008,5120env/horizon32/LR5e-5,fullresetnoise,2mm/.3s,proximity.1,posecost1withoutnewramp. Namedtasks use support40mrad or200mrad; officialhandprofile changesgains+armature only. Frozen .04/.20/.40rad policies scored23/1/0,23/0/0,13/0/0per100, so directactionscalingfailed. Botharms were declaredbefore the.4result and require actual3epochpreflights. Five-minute monitors andCP10/25/50/75/100100savedstateaudits use matchingnamedtask/hand, neverolddefaultactions. Not a fullofficialMuJoComodel orhardwarecalibration.


04:39 observed: both officialactuator3epochpreflights and hold2preflight exited0 and their formalteachers started. Hold03 still awaits its predecessor. Continuouscost1CP100 development100/100strict-first,86/100full led to a predeclared fresh12203/13313 plus2s/5stimedqueue before those results existed. CP50nominal30/32versus4/32full contrasts with matched perturbation74/100versus74/100, so posecost conclusions are condition-specific. All originalbaselines and resource monitors stayactive.
