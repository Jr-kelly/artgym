# ArtBot Wuji right hand

Extracted from `/data/research/ArtBot/G2_crsB_wuji/robot.usd` on 2026-09-20.
The whole source asset was copied into the locally ignored `source/` directory.
`right.urdf` and `meshes/` are self-contained; running ArtGym does not require USD.
`source_hashes.yaml` records the source layers used by the exporter.

The hand has 20 actuated revolute joints and 26 rigid bodies. Joint order is
index, middle, pinky, ring, thumb, with joints 1–4 for each finger. Contact and
tracking links are ordered thumb, index, middle, ring, pinky. These orders serve
different purposes and must be preserved when generating grasps or sending actions.

Joint frames, limits, effort limits, velocity limits, masses, centers of mass,
and inertia tensors come from the USD. Angular limits/velocities are converted
from degrees to radians. Drive stiffness/damping are converted from per-degree
USD units to per-radian Isaac Gym units (approximately 100 and 1). No armature or
joint friction is authored for these hand joints, so those values are zero.
Self-collision is disabled, matching the source articulation configuration.
These are simulation parameters, not calibrated hardware parameters.

The source hand's collision nodes are empty. The exporter builds convex hulls
from the visual meshes. For each distal link, the final 14 mm is assigned to the
fixed fingertip pad; the remaining hull stays on link4. This avoids assigning
overlapping copies of the entire distal link to both bodies. It is an approximate
contact model that will need validation against the actual hand before hardware
transfer. Rendered materials use simple colors; source textures are not exported.

The zero-joint-position link transforms were compared against the source USD:
maximum absolute transform matrix difference was below `6e-7`.

To regenerate, use a separate Python 3.10+ environment with `usd-core`, `numpy`,
`scipy`, and `pyyaml` (USD tooling is separate from the Python 3.8 simulator):

```bash
tmp/wuji-usd-tools/bin/python scripts/import_wuji_artbot.py \
  --source assets/hands/wuji_artbot/source/robot.usd
cp assets/hands/wuji_artbot/hand_config.yaml isaacgymenvs/cfg/hand/wuji.yaml
```

The repository's original `assets/hands/wuji/right.urdf` is a different version
and was left in place. `hand=wuji` now selects this ArtBot-derived asset.
