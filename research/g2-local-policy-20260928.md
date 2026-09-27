# G2 + Wuji local policy — 2026-09-28

Active new authorized24h task. Start Sep28 01:53:41 CST, deadline Sep29 01:53:41; delivery starts Sep29 00:23:41. Local4090 only, cumulative12GPUh, at most2routes/4configs; control development80trials, rounds<=12. No old tasks stopped. Original teacher completed50,000epochs exit0 Sep27; monitors preserved.

State: `runs/g2-local-policy-20260928/state.json`. Worktree `/data/research/artgym-g2-local-policy-20260928`, branch `feat/g2-wuji-local-policy-20260928` from verified3985cb8.

## Immutable evidence and scope
Full G2 servo and original physics. Local reset from recorded real R3-12/R3-13 tail, NOT continuous acquisition. Original teacher/student frozen. H22s; S20s clock reversal5s lowerlimit0/+40mm. Fixedworld10mm/0.25rad, endpoint last0.3s10mm/2mm. No object writes outside resets.
Reuse R3-12 fullteacher failure, R3-13 static rotation instability, R3-14 thumb-only42mm but firstcycle/stability fail, R3-15 independent presetA success, R3-16 middlefeedback contact improved but instability. Development evidence only.

## Round1 preregistration — <=8 local diagnostic executions
Hypothesis: recorded q/qd, body pose/vel, arm integral and motor refs produce a comparable support problem despite missing PhysX contact cache. Compare fixedH and fullteacher/thumb-onlyS to continuous tail. No extra settling initially; record firststep jump and later failure type. Repeated resets and parallel isolation check. If inconsistent inspect state/coordinates/servo before learning. Count per-env diagnostic episodes, training separate.

Next: faithful localenv, baseline comparison, end-to-end throughput. Declare routeA bounds before optimization.

## Prototype and R1-01 (02:03 CST)
Local fullG2 environment and smallPPO implemented; no optimization yet. Prephysics import failed once because conda bin absent from PATH (ninja unavailable); corrected invocation, log retained. R1-01 H initial q/qd/root exactly source. Firststep7.07micrometre/.0000265rad change, arm differs continuous<1microrad. StaticH22s fails .5128rad with firstfailure18.533s vs original~4.73s/.5922rad. Initial contact/dynamics sensitivity causes meaningful timing discrepancy; not claimed equivalent. No physicalprops intentionally changed. S thumb-only comparison running.

## Learning configuration A1 preregistration
RouteA support-only16joints; teacher thumb fixed in H and frozen thumb-only teacher in S (separateA2). Residual absolute target offset<=.20rad, target speed<=.60rad/s, hardware limits unchanged. New controller, not originalteacher. All 16supports can adapt; objecttruth privileged. MLP128x128 actor/value, PPO clip.2, gamma.995 lambda.95, lr3e-4, rollout64,4epochs, init Gaussianstdexp(-1.5). H22s from actualframe2248. Reward explicit fixedworld translation/rotation shaping, sliderstationarity and actionregularization; success independently full22s10mm/.25rad. First pilot includes fullstep/reset/obs/inference/update/logs, actual optimization counted as configuration1 and learningGPUtime. Start with32envs/10updates if reset checks acceptable; earliest deterministic eval afterupdate1. No claims of generalization from replicas of one source.

R1-02 local thumb-onlyS:45.73mmtravel, endpoints24.88/0/5.12/0mm,19.52mm/1.0568rad world; instability5.033s vs continuous5.067s. Same firstcycle/stability failure with comparable onset. H discrepancy remains documented. R1-03 two environments x2 fixedH episodes begins (total6 diagnostic physics executions allocated). No learning started.

Batched frozen-teacher bridge checked offline against original first takeover: FK max3.73e-8m, observation1.35e-7, raw/executed action1.79e-7; commanded hand targets exactly equal. This checks interface conversion, not dynamics equivalence. Code published at https://github.com/Jr-kelly/artgym/tree/feat/g2-wuji-local-policy-20260928 .

R1-03 found an implementation bug before learning: this installed CPU tensor pipeline uses per-environment world coordinates for root/RB states. Grid origins must not be added/subtracted. Env0 reproduced R1-01; env1 knife reset+4m while robot remained local (wrist was incorrectly reported-3.665m), so dropped. First2traces retained; second pair interrupted once identified (4physicalepisodes started counted,2incomplete). Querying actor states/root tensors before simulation confirmed frame convention. Fix removes origin conversion and refreshes initial root tensor. This is environment repair, not a physical/control change. R1-04 predeclared2env fixedH22s verifies fix; cumulative8diagnostic executions.

Targeted firststroke audit (oldR3-14, not a newtrial): thumbq4 command starts1.25rad and decreases to-.442rad by4.97s; slider stays closed at4.0s and reaches20.52mm at4.97s. At4.7s endpoint window begins but displacement still~13mm. Secondcycle succeeds afterq4 has reached lowerstop. This suggests a possible coordination/initial articulation transient to test after supportlearning; not established as solecause. Do not spend the wholebudget forcing unchanged thumbbehavior if supportS cannot improve endpoint metrics. Bounded joint residual is authorized fallback, not yet launched.

R1-04 corrected2env H: no drop, rotation.5128/.5593rad; firstinstability18.533/16.933s. Env0 reproduces singleenv; env1 now aligned and same failure class. Proceed A1-H-pilot32env,10updates,max.4GPUh including earlyevaluation. This is actual PPO optimization, source pinned by launch manifest.

A1-H-pilot actually optimizing since02:10:50 CST:32env,2048transitions/update, first complete pipeline17.81s inclsetup;114.98transitions/s, update15.17s;53training episodes ended,0success; earliest deterministic660step evaluation in progress. GPU94%, memory~2.1GB at02:12 CST. Nominal learningGPUtime budget<=.4h forpilot. Reward is not success.

Continuous motor-only learner runtime implemented (not yet physically evaluated). Offline first-command audit: {"first_action_max_error": 2.0954757928848267e-09, "first_hand_target_max_error": 0.0, "initial_reference_fixed": [[0.44358885288238525, -0.30063194036483765, 1.0520284175872803, 0.5407782196998596, 0.002578476909548044, 0.20184099674224854, 0.8165857791900635]], "scope": "offline runtime vs actual learned eval first command; no new physics episode"}

## A1 pilot result and Round2 preregistration
Pilot443.99s=0.12333GPUh,20480sampled transitions/369ended trainingepisodes, actualPPO. Evalupdate10:13/32 passfullH22s10mm/.25rad, update1was0/32. Same acquiredsource, repeated numerical replicas, notgeneralization. Meanrotation.978rad is skewed by8largeescape cases; successmetricpreserved. Earlypilot eval savedall32scores but rawtracesonlyfirst4 (limitation); allsubsequent evals saveallreplicas. More successful H justifies sameA1 continuation240updates,max1.5GPUh; sameAdam andmodel.
Round2<=8 motorcontrol diagnosticexecutions predeclared: fresh2env learnedH x2episodes (4), localfullteacherS(1), conditionallycontinuousH(1), leave2unallocated. Check resetcache dependence and originalbaseline. No property/controlbounds change. Trainingepisodes and internalmodel-selection evaluations separately logged.

R2-01 fresh simulator first2 learnedH episodes:bothpassed22s, worldtranslation.523/.542mm,rotation.0286/.0405rad, no drop. Same source and pilotupdate10, notnewplacement. This is much more stable than fixedH. Repeated-reset pair stillrunning; no continuousH result yet. R2-01 sourcepin writesboth22s episodesintoone video; it will be splitexactlyatframe660 into separateepisode files before delivery; never presentedasonecontinuous44s acquisition. Subsequent runner writesseparatevideos natively.

R2-01 completed:4/4 localHpass (2envs,2resets,1actualsource), maximum.5425mm/.04055rad, no drop. Real elapsed450.10s with video whiletraining sharesoneGPU; not a barephysics throughput figure. R2-02 actual continuous tableprefix→samepilot10 H22s launched; no injectedlocalreset and noSsuccessclaim. Motorcontrol development count13started.
