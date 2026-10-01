> Wuji迁移的最新入口：[实验结果、代码、全量备份及恢复说明](docs/wuji/README.md)。

# ArtGym

This repository is the official implementation of **ArtManip: Category-Level Articulated In-Hand Manipulation**.

[Paper](https://arxiv.org/abs/2609.12498) · [Project Page](https://artmanip.github.io/)

ArtGym contains Isaac Gym environments and scripts for articulated-object grasping, manipulation, teacher training, student distillation, and simulation evaluation.

<!-- WUJI_STUDENT_CURRENT -->
## Wuji unified student — frozen results, 2026-10-01

**One student can execute slider cycles, but does not meet the full strict-stability gate.** These are once-opened, independently rescored H200 final results, **128 episodes per source and protocol**; every table entry is out of128. They concern the existing simulated knife and three grasp clusters (nearby sources0/1, source2, source3), not hardware or unseen-grasp generalization.

| Policy | S2 strict, sources 0/1/2/3 | S5 strict, sources 0/1/2/3 | Minimum S2 / S5 body stability |
|---|---|---|---|
| Eagg6100 teacher | 128,127,126,105 | 125,128,127,112 | 125 / 125 |
| SA-51200 selected student | 126,120,117,93 | 126,121,122,97 | 121 / 124 |
| SA-70400 fixed endpoint | 114,108,113,94 | 106,97,83,84 | 120 / 122 |
| SC-51200 equal-update latent control | 120,119,115,77 | 115,123,117,62 | 124 / 124 |
| C1 initial-only reference | 0,0,0,0 | 0,0,0,0 | 0 / 0 |

The selected student's worst strict result is source3 S2 **93/128 (72.7%)**, with body stability121/128 (94.5%); source3 S5 is97/128 (75.8%). Sources0/1/2 pass their S gates. F completes a cycle in[128,128,128,126]/128, while full40-second body stability is[124,106,128,110]/128. Cycle completion is distinct from stability.

The student requires calibrated initial object geometry/poses, joint and action history, realizable hand FK, known controller targets and external commands. It does not read runtime object state or call the teacher encoder. The F benchmark's external command generator uses true slider arrival; sensor-free arrival detection and real calibration are unverified.

At the same51200 optimizer counter, executed-target supervision improves7/8 strict source/protocol cells and worst strict93/128 versus62/128 for latent-only control, with body/F tradeoffs. Development gains vary by checkpoint; there is no second optimization seed or convergence claim. Both continuous branches completed70400; the chosen weight was fixed before final access.

Public distribution verification passed: actual primary/video downloads, restored-code policy checks and full video decoding ([receipt](research/unified-student-20261001/public-verification.json)).

[Final report, intervals and paired transitions](research/unified-student-20261001/FINAL_REPORT.md) · [Method and limitations](research/unified-student-20261001/README.md) · [Input audit](research/unified-student-20261001/INPUTS.md) · [Reproduce](research/unified-student-20261001/REPRODUCE.md) · [Release](https://github.com/Jr-kelly/artgym/releases/tag/wuji-unified-student-20261001-v1) · [Teacher/student video](https://github.com/Jr-kelly/artgym/releases/download/wuji-unified-student-20261001-v1/teacher-student-fixed-comparison.mp4)
<!-- /WUJI_STUDENT_CURRENT -->

## Clone

Clone the repo with submodules:

```bash
git clone --recursive git@github.com:youngcv/artgym.git
```

If you already cloned without `--recursive`, initialize the submodules with:

```bash
git submodule update --init --recursive
```

## Installation

see [install.md](install.md) for installation.

For the ArtBot Wuji right-hand port, a runnable 40 mm utility-knife slider demo,
grasp generation, and training commands, see [wuji.md](wuji.md).

## Submodules

Additional documentation lives in the linked submodules:

- [make_data/README.md](make_data/README.md)
- [func_lygra/README.md](func_lygra/README.md)

## Prerequisites
- Using [make_data](make_data/) to generate ./assets/objects/...
- Using [func_lygra](func_lygra/) to generate ./caches/initial_grasp/...

Verify the file structure matches:

```
./assets/hands/...
./assets/objects/...
./caches/initial_grasp/...
```


## Pipeline

This is the main workflow:

- validate grasps in sim
- train teacher
- evaluate teacher
- save a `success` grasp pool
- select a grasp and run teacher inference in sim
- distill and evaluate the student in sim

### 1. Validate Grasps

Validate all instances of one object class:

```bash
scripts/validate_all_instances.sh \
  sharpa knife \
  --asset-dir knife_30 \
  --pipeline cpu \
  --num-envs 500 \
  --episode-length 30 \
  --rot-threshold 0.1 \
  --pos-threshold 0.01 \
  --no-split \
  --headless \
  --camera
```

Save a deduplicated grasp pool with `--unique`:

```bash
scripts/validate_all_instances.sh \
  sharpa knife \
  --asset-dir knife_30 \
  --pipeline cpu \
  --num-envs 500 \
  --episode-length 30 \
  --rot-threshold 0.1 \
  --pos-threshold 0.01 \
  --unique \
  --unique-pos-threshold 0.005 \
  --unique-rot-threshold 0.05 \
  --no-split \
  --headless \
  --camera
```

Validate one instance:

```bash
python -m isaacgymenvs.valid_grasp \
  --pipeline cpu \
  --hand sharpa \
  --object knife \
  --asset-dir knife_30 \
  --instance-id 000 \
  --num-envs 500 \
  --episode-length 30 \
  --rot-threshold 0.1 \
  --pos-threshold 0.01 \
  --headless \
  --camera
```

The unique filter removes a grasp only when both are true:

- object position distance is below `--unique-pos-threshold`
- object rotation distance is below `--unique-rot-threshold`

### 2. Train Teacher

```bash
python -m isaacgymenvs.train \
  task=artmanip \
  hand=sharpa \
  object=knife \
  asset_dir=knife_30 \
  train=artmanipSAPGPrivLSTMPPO \
  task.env.numEnvs=16000 \
  experiment=knife_sapg \
  headless=True \
  task.env.graspSplit=valid
```

Single-machine multi-GPU training:

```bash
CUDA_VISIBLE_DEVICES=0,1 torchrun --standalone --nnodes=1 --nproc_per_node=2 -m isaacgymenvs.train \
  task=artmanip \
  hand=sharpa \
  object=knife \
  asset_dir=knife_30 \
  headless=True \
  train=artmanipSAPGPrivLSTMPPO \
  task.env.numEnvs=16000 \
  experiment=knife_sapg \
  task.env.graspSplit=valid \
  multi_gpu=True
```

`task.env.numEnvs` is per GPU.

### 3. Evaluate Consecutive Teacher Success
Evaluate one instance:

```bash
python -m isaacgymenvs.eval_consecutive \
  --checkpoint runs/knife_sapg/best/model.pth \
  --train artmanipSAPGPrivLSTMPPO \
  --hand sharpa \
  --object knife \
  --asset-dir knife_30 \
  --instance-id 000 \
  --grasp-split valid \
  --max-steps 1200 \
  --episodes-per-grasp 100 \
  --goal-switch-interval-secs 1.5 \
  --save-success-cycle-threshold 1.0 \
  --save-success-cycle-metric mean \
  --save-success-output-split success \
  --deterministic \
  --headless \
  --randomize true
```

Use this to rank grasps by how many open-close cycles they sustain before failing.

`--grasp-split` can be `train`, `test`, `valid`, `select`, or `success`.

This writes:

- `caches/initial_grasp/sharpa/<asset_dir>/<instance_id>/consecutive_eval_summary.json`

With threshold-based saving, it also writes:

- `caches/initial_grasp/sharpa/<asset_dir>/<instance_id>/success/valid_grasps.npy`
- `caches/initial_grasp/sharpa/<asset_dir>/<instance_id>/success/summary.json`

Batch-evaluate all instances:

```bash
bash scripts/eval_consecutive_all_instances.sh \
  sharpa knife \
  --asset-dir knife_30 \
  --checkpoint runs/knife_sapg/best/model.pth \
  --train artmanipSAPGPrivLSTMPPO \
  --grasp-split valid \
  --max-steps 1200 \
  --episodes-per-grasp 100 \
  --goal-switch-interval-secs 1.0 \
  --save-success-cycle-threshold 0 \
  --save-success-cycle-metric mean \
  --save-success-output-split success \
  --deterministic \
  --headless \
  --randomize true
```

This saves:

- `caches/initial_grasp/sharpa/<asset_dir>/<instance_id>/consecutive_eval_summary.json`
- `caches/initial_grasp/sharpa/<asset_dir>/consecutive_eval_asset_summary.json`


### 4. Infer The Teacher In Sim
Choose one cached grasp before inference:
```bash
python select_grasp.py \
  --hand sharpa \
  --object knife \
  --asset-dir knife_30 \
  --instance-id 000 \
  --group success \
  --select-idx 0
```
```bash
python -m isaacgymenvs.infer teacher \
  --train artmanipSAPGPrivLSTMPPO \
  --hand sharpa \
  --deterministic \
  --randomize false \
  --goal-switch-interval-secs 1.5 \
  --max-steps 300 \
  --save-cur-targets cur_targets.npy \
  --save-video infer.mp4 \
  --headless \
  --checkpoint runs/knife_sapg/best/model.pth \
  --object knife \
  --asset-dir knife_30 \
  --instance-id 000
```

`--goal-switch-interval-secs` is the success-hold time before infer switches between goals.


### 5. Distill Student

```bash
python -m isaacgymenvs.distill \
  --checkpoint runs/knife_sapg/best/model.pth \
  --train artmanipSAPGPrivLSTMPPO \
  --hand sharpa \
  --object knife \
  --asset-dir knife_30 \
  --num-envs 8000 \
  --updates 10000 \
  --rollout-steps 16 \
  --lr 1e-4 \
  --cosine-coef 0.1 \
  --deterministic \
  --expl-block-idx 0 \
  --headless \
  --save-every-updates 100 \
  --save-best-after-updates 500 \
  --grasp-split valid \
  --custom_tcn
```

When using RTX 50s gpu, --custom_tcn is necessary.

Single-machine multi-GPU distillation:

```bash
CUDA_VISIBLE_DEVICES=0,1 torchrun --standalone --nnodes=1 --nproc_per_node=2 -m isaacgymenvs.distill \
  --multi-gpu \
  --checkpoint runs/knife_sapg/best/model.pth \
  --train artmanipSAPGPrivLSTMPPO \
  --hand sharpa \
  --object knife \
  --asset-dir knife_30 \
  --num-envs 8000 \
  --updates 100000 \
  --rollout-steps 16 \
  --lr 1e-4 \
  --cosine-coef 0.1 \
  --deterministic \
  --expl-block-idx 0 \
  --headless \
  --save-every-updates 100 \
  --save-best-after-updates 500 \
  --grasp-split valid \
  --custom_tcn
```

`--num-envs` is per GPU, and only rank 0 writes checkpoints, summaries, and periodic eval outputs.

Distillation saves:

- best-loss distilled checkpoint at the resolved student output path
- best-reward checkpoint beside it, named like `proprio_only_best_reward.pth`
- optional periodic checkpoints like `proprio_only_update0100.pth` when `--save-every-updates` is enabled

Use `--save-best-after-updates 50` to delay best-loss and best-reward checkpoint tracking.

### 2. Evaluate Student

```bash
python -m isaacgymenvs.eval_consecutive \
  --student-artifact runs/knife_sapg/nn/student/proprio_only_update0100.pth \
  --checkpoint runs/knife_sapg/best/model.pth \
  --train artmanipSAPGPrivLSTMPPO \
  --hand sharpa \
  --object knife \
  --asset-dir knife_30 \
  --instance-id 030 \
  --grasp-split valid \
  --episodes-per-grasp 100 \
  --goal-switch-interval-secs 1.5 \
  --max-steps 1200 \
  --deterministic \
  --torch-deterministic true \
  --headless \
  --randomize true \
  --progress-interval-sec 2
```

evaluate all instances:

```bash
bash scripts/eval_consecutive_all_instances.sh \
  sharpa knife \
  --asset-dir knife_30 \
  --student-artifact runs/knife_sapg/nn/student/proprio_only_update0100.pth \
  --checkpoint runs/knife_sapg/best/model.pth \
  --train artmanipSAPGPrivLSTMPPO \
  --grasp-split valid \
  --episodes-per-grasp 100 \
  --goal-switch-interval-secs 1.0 \
  --max-steps 1200 \
  --deterministic \
  --headless \
  --randomize true \
  --save-success-cycle-threshold 0 \
  --save-success-cycle-metric mean \
  --save-success-output-split success_student
```

### 3. Infer Student

```bash
python -m isaacgymenvs.infer student \
  --student-artifact runs/knife_sapg/nn/student/proprio_only_update0100.pth \
  --checkpoint runs/knife_sapg/best/model.pth \
  --train artmanipSAPGPrivLSTMPPO \
  --hand sharpa \
  --object knife \
  --asset-dir knife_30 \
  --instance-id 000 \
  --deterministic \
  --torch-deterministic true \
  --randomize false \
  --goal-switch-interval-secs 1.5 \
  --max-steps 300 \
  --save-cur-targets student_cur_targets.npy \
  --save-video student_infer.mp4 \
  --headless
```

## PPO Variant

To run PPO instead of SAPG, use the same commands and change only the train config name from `train=artmanipSAPGPrivLSTMPPO` to `train=artmanipPrivLSTMPPO`.

## Real-World Deployment

refer to [deploy.md](deploy.md) for details

## Acknowledgements

We thank the authors and contributors of [SimToolReal](https://simtoolreal.github.io/), [Lightning Grasp](https://github.com/zhaohengyin/lightning-grasp), and [Hora](https://github.com/HaozhiQi/hora) for sharing their code and research with the community. We appreciate their contributions to open-source robotics research.

## Citation

If you find this work useful in your research, please cite:

```bibtex
@article{yang2026artmanip,
  title={{ArtManip}: Category-Level Articulated In-Hand Manipulation},
  author={Yang, Yang and Liu, Tengyu and Li, Puhao and Chen, Zeyuan and Li, Yuyang and Wang, Xingwan and Wu, Yingying and Cui, Zhaopeng and Huang, Siyuan},
  journal={arXiv preprint arXiv:2609.12498},
  year={2026}
}
```
