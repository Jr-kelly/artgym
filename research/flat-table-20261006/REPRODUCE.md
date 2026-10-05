# Reproduce the new flat-table physical attempts

Use the existing contact-transfer-v1 restored runtime and assets. This is a **failed full-task candidate**, not a completed pickup policy. Workspace: `/data/research/artgym-experiments-20260921/flat-table-20261006`.

```bash
source runs/contact-transfer-20261006/env.sh
python -m scripts.run_wuji_flat_table \
  --output runs/flat-table-20261006/reproduce/<new-directory> \
  --resistance runs/singlepush-20261005/configs/resistance-0.73549875.json \
  --reference-control-config runs/singlepush-20261005/configs/reference-path-drive.json \
  --flat-table-prefix runs/flat-table-20261006/preparation/push-corner-v10/prefix.json \
  --postpush-pose-update
```

The initial knife is fully on the fixed table: root (0.370,-0.5695,0.7541)m, yaw45°. Table x=[0.3,0.9], y=[-0.63,0.17], surface z=0.75m. Entire nominal144×19mm footprint is inside these bounds. Robot pushes, withdraws, reads one declared simulation pose, regenerates acquisition/transfer IK, attempts pickup and operates. Original gravity, friction, torque clipping and contact remain; no interstage object/joint reset. The operation fails because the functional grasp's ring/pinky approach remains obstructed by the table. The knife is not lifted.

Choose another stored prefix to reproduce other development placements/actions. The baseline two-pad path is `push-v5/prefix.json`; corner-v10 adds fixed-world-X motion. Files are immutable experimental candidates, not asset-ID selection.

Pose interface: `--postpush-pose-input observation.json` supplies an explicit postpush estimate in place of oracle; enable `--postpush-pose-update`. JSON requires `frame: robot_base`, `units: m_rad`, `source: sim_estimate` or `real_vision`, and a4×4 `object_world_matrix`. The matrix uses metres with rotation matrix convention; timestamp should be supplied for a future live provider. `--pose-estimate-bias-m` injects independent estimator X bias while physical placement remains fixed. These routes exist but were not physically validated with error or real vision. One oracle update assumes knife visible after withdrawal. Actor retains the old estimated relative-grip prior; no claim of successful consumption of arbitrary grasp errors.

Baseline actor SHA256: `6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e`.
Previous successful edge-start1.25N24.366mm source/video remain in contact-transfer release; this round does not replace that evidence.
