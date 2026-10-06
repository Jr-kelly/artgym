# Functional inverse round: actual new table handoff

Original whole-flat pickup v123 remains A-only. New native behavior: loaded finger-coordinated table transport71mm, near-corner correction, passive thumb release in recorded short entry; new tilted index/middle contact; index-supported joint wrist transition followed by actual thumb slider contact. Last rail-clear short entry keeps index throughout9s, root drift0.391mm, thumb contacts slider59 recordedframes from3.567–9s. It remains table supported. Active stroke is in development; no complete A→B or generalization claim.

One continuous72.1s validation from original flat start retains clamp through64s, but prior corner release ejects knife. Actual-pose normal withdrawal also ejects it after thumb unload: loaded index requires opposition before release. Stop this passive-release branch.

Restore entries contain actual object13state, robot positions, slider, issued motor targets/history; robotvelocity finite-difference, PhysX warmstart absent. Development only, not exact resume equivalence. Actor unchanged 6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e. Original finitePD, gravity/effort/friction/resistance retained. No realrobot/realvision. Filter originalnotice preserved; no blanket experimentban established.

Reproduce from experimentroot after source runs/contact-transfer-20261006/env.sh. Run scripts/run_wuji_saved_command.py with pertrial command.json; necessary short actualstate entries and motorpaths are in progress archive. Existing A-only entry remains python -m scripts.run_wuji_flat_table_pickup_selected --output <fresh>.
