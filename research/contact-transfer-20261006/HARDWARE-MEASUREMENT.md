# Same-grasp G2 + Wuji v1 measurement and control interface

The existing `HandAPI` now has `isaacgymenvs.deploy.wuji.sdk_hand_api.WujiSDKHandAPI`.
Its encoder output and commands use the actual configured runtime joint names;
`joint_mapping.py` alone converts to SDK thumb/index/middle/ring/pinky, four joints
per finger. Runtime is index/middle/pinky/ring/thumb. SIM→SDK blocks [4,0,1,3,2];
inverse [1,2,4,3,0]. MAPPING-CHECK.json verifies20 distinct values and real saved
postures. Physical joint axis signs, zero offsets and actual device limits remain
unverified. Mapping arrays are never exposed without names, units and source.

Installed and imported official wujihandpy1.8.0 in an isolated Python3.10 venv;
actual constructor/read/realtime signatures checked. Python3.8 selected1.7.0
failed import (`typing.Annotated` unavailable), so do not install that wheel into
the Isaac Gym environment. Runtime and SDK remain separate environments. Actual
SDK-shaped fixture validates mapping, read-only refusal and permitted fixture
position writes: zero physical device writes. This is not a connected-hand test.

```bash
python3.10 -m venv sdk-venv
sdk-venv/bin/pip install 'wujihandpy==1.8.0'
sdk-venv/bin/python -m scripts.record_wuji_same_grasp --output runs/device-discovery
# Only after identifying the exact right-hand serial, read-only:
sdk-venv/bin/python -m scripts.record_wuji_same_grasp --serial EXACT_SERIAL \
  --seconds 3 --external-jsonl /path/to/live-force-meter.jsonl --output runs/same-grasp-read
```

Discovery uses USB sysfs VID0483/PID2000 from official SDK defaults; installed
SDK1.8 has no public device enumeration API. No matching devices observed locally
or on the supplied SSH server. This establishes no completed device connection,
not absence of a hand elsewhere. Discovery does not instantiate `Hand`, enable
joints, start realtime control or change effort/current limits.

The default adapter refuses position writes. An existing authorized realtime
controller can be injected; actual effort is read using its
`get_joint_actual_effort()` only. Without it, effort stays null. Effort and its
limit are SDK filtered drive quantities in A, never Nm or contact force. Limits
come from device reads, never hardcoded1.5A. The API cannot read actual target
position in this version; record successful writes/host timestamps and explicitly
mark target readback unavailable. Host read boundaries and raw device time are
retained; raw uint32 device-time scale/wrap needs firmware confirmation.

| Existing simulation component | Deployment location / remaining calibration |
| --- | --- |
| 30Hz measured q, FK,50 actual q/action frames | Existing policy/history and observation provider; mapped SDK encoders supply runtime q. Real measured warmup, not synthetic history. |
| Scheduled reference and bounded residual | Host produces position targets. Retained actor/control assets unchanged. |
| Pressure proxy from q/target error and simulated Kp | Host software position offset only; disable pending measured local stiffness/response verification. Never call this true force. |
| Tangent FK tracking correction | Host position adjustment; actual self-clearance still must constrain final corrected output. Strict near-small setpoint guard yields14.56mm, but actual29.71mm motion stays>=11.78mm clear; this is an impedance calibration issue, not a hard hand-space limit. |
| 240Hz explicit finite-PD + gravity compensation | Simulation motor layer only. Do not send extra torque/gravity terms on top of SDK firmware position control. Firmware stiffness/latency unknown. |
| G2 seven arm joints, pickup/regrasp wrist trajectory | Existing saved motor paths and named joint limits; actual G2 arm backend/feedback/authorization not connected or verified here. |

External force-meter JSONL observations carry `host_monotonic_ns`, `station`
(start/middle/end), `axis` (normal OR axial), `force_N`, `source`, material and
actual displacement/slip notes. Appended observations are consumed during polling;
raw observations and alignment age are retained. Each force axis must be aligned
separately. `sample(external_force)` can also be called from the existing
position-control loop so issued targets and optional realtime effort are logged
at the actual control cycle. A stale/mixed-direction reading is not a valid
sustained-force sample.

The recorder was executed on181 saved simulation samples with named measured q,
issued targets, actual clipped motor Nm and calibrated rail capacity. No external
force values were fabricated. `scripts.analyze_wuji_same_grasp_response` runs on
these records and gives descriptive target/encoder correlation, not identified
firmware Kp or a hardware calibration curve. For real force samples it reports
start/middle/end, separately aligned axis, min/mean/peak and >=1s duration.

Next real session needs only: actual right-hand/G2 connection and motion
authorization; verify calibrated axes/zeros/limits/current restrictions and timing;
measure identical knife/contact material at start/middle/end with separate normal
and rail-axis forces for>=1s, actual displacement/slip and known0.7355/1.0/1.25N
loads. Read startup/along-slot resistance and fit local response only from real
measurements. Near-small target-only overlap differs from its clear actual measured motion.
Verify firmware/current/contact-loss response instead of treating abstract preload
targets as realized positions or blindly increasing effort limits.

Official interface references: https://docs.wuji.tech/docs/zh/wujihandpy/latest/introduction/
and https://docs.wuji.tech/docs/zh/wujihandpy/latest/api-reference/ .
