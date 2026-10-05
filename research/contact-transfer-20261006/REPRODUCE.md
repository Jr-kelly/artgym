# Contact-transfer reproduction

Run in a compatible Python3.8/Torch1.13/Isaac Gym Preview4 environment. Import
Isaac Gym before torch. Use `runs/contact-transfer-20261006/env.sh` with your
runtime paths. Outputs must be new directories; these commands only simulate.

```bash
python -m scripts.run_wuji_contact_transfer_selected --output runs/my-reference
python -m scripts.run_wuji_contact_transfer_selected --load 1.25 --output runs/my125
python -m scripts.run_wuji_contact_transfer_selected --case near-small --output runs/my-near-small
python -m scripts.run_wuji_contact_transfer_selected --case mid-high-delay --output runs/my-frozen-mid
python -m scripts.run_wuji_contact_transfer_selected --case upper-geometry-friction --output runs/my-frozen-upper
# Explicit failed development contrasts:
python -m scripts.run_wuji_contact_transfer_selected --case near-small-guard --output runs/my-guard
python -m scripts.run_wuji_contact_transfer_selected --case large-center --output runs/my-large
```

Add `--no-video` on servers without graphics. Every run is a continuous22s actual
simulation: table pickup, motor regrasp ending14.2s,50 real measured history
frames, forward command at16s, position hold after20.033s. No return, state/history
reset, live object/slider/contact/force/load-ID policy input or object fixture.
Original extension-only criterion remains unchanged. Exit0 means completed run,
not task pass; read `simulation/extension-evaluation.json`. Nominal1.25N24.366mm,
near-small29.713mm and frozen-mid22.123mm pass physical task. Frozen-upper and
listed development contrasts fail. Actual corrected near-small pose clearance
checks pass; the strict target-only guard is a deliberately conservative negative
comparison, not the selected controller or a new task acceptance rule.

## Small overlay over already restored dependencies

Use the previous verified singlepush runtime. For first installation, follow
[the prior reproduction](../singlepush-20261005/REPRODUCE.md) and the unchanged
[wrap dependencies](https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-wrap-force-20261005-v1):
`wrap-runtime.tar.gz` SHA2563641e30850d88a41a5db4c385ff06d50ca321bc1f47e6527cd23fdcbd1a43fab;
`wrap-learning-state.tar.gz` SHA256519d9dc52d7cb1091da79901268933e8ccabfa908425bd1b1ccdc98ec84039b4.
Those large packets were not repackaged. This round's overlay inherits the verified
singlepush file list and contains all new source/assets/preparation/configuration.

```bash
python -m scripts.restore_wuji_contact_transfer \
  --verified-base-root /path/to/verified-singlepush-root \
  --overlay /path/to/contact-transfer-overlay.tar.gz \
  --destination /path/to/new-empty-root --run
```

It copies the already verified runtime, checks every new overlay file against
`recovery-manifests/contact-transfer-overlay-files.json`, then runs one1.25N
representative. It does not claim to independently rehash every old dependency.
RESTORE-VERIFICATION.json records the result and expected exact1.25N trace hash.
Licensed Isaac Gym must be installed independently. `contact-transfer-evidence`
contains new raw traces, normal-contact records, certificates and rejection logs.
`contact-transfer-video-report.zip` contains browsable HTML and all24 new MP4
views; individual MP4 assets are also supplied. No private Goal HTML or photos.

Source actor is unchanged, SHA256
6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e.
Training-fit provenance is distinct from these frozen/independent physical checks.
No new training. Full-normal large32.408mm is explicitly diagnostic: it requires
original command rate limiting and fails body rotation, so the selected entry
correctly refuses to promote its uncertified nominal rate path.

See HARDWARE-MEASUREMENT.md for the separate pinned SDK1.8/Python3.10 environment,
read-only hardware discovery/telemetry and same-grasp real measurement inputs.
Do not send simulation PD/gravity torques on top of firmware position control.
