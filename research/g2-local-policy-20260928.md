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
