# Proposed autonomy contracts (v0.2.0-proposal)

Author: Claude. **Proposal for Codex to consolidate into `contracts/`.** Reference implementation:
[`autonomy/contracts.py`](../../autonomy/contracts.py). Nothing here is integration-tested against the
simulator yet.

## Conventions

| Item | Convention |
| --- | --- |
| Units | m, rad, s, m/s, rad/s |
| Time | `timestamp` = robot monotonic clock (float s). Sim publishes sim time on the same field. Every message carries one. |
| `map` frame | z up, floor z = 0, fixed per episode; origin = prior floor plan origin |
| `base` frame | x forward, y left, z up, origin on the floor under the pelvis |
| Camera frame | OpenCV optical (x right, y down, z forward). MuJoCo/Isaac OpenGL cameras: `T_cv = T_gl @ diag(1,-1,-1,1)` |
| Depth | metric **z-depth** (not ray length); 0 / NaN / inf = invalid |
| Missing data | the field is `None`; never zeros as a stand-in |

## Provenance (on every input)

`measured` (real or simulated sensor emulation: rendered RGB/depth, IMU, joint encoders),
`estimated` (odometry/VSLAM/detector output), `operator` (instruction, map annotations),
`sim_privileged` (ground truth: exact pose, object ids, rendered instance masks, contact forces).

**Rule**: `sim_privileged` may feed evaluation, training labels and diagnostics only.

**Privilege propagates (taint rule).** Anything derived from a privileged input is privileged,
even if the other inputs are deployable:
- detections from rendered masks or labels;
- scene-memory entries fused from those detections;
- grounding verdicts, executive decisions and VLA state/text features built from that memory.

A run is deployable only if every input in its derivation chain is. A deployable raw RGB frame
does not launder masks-derived memory. Episode and experiment metadata must list all privileged
inputs.

`Observation.assert_deployable()` raises on privileged pose or segmentation, and
`DeliveryExecutive(deployable=True)` refuses privileged detectors. Codex's sim adapter should set
provenance honestly; the guard is a backstop, not a substitute.

## Sim/robot → autonomy: `Observation`

| Field | Type | Notes |
| --- | --- | --- |
| `timestamp` | float | snapshot time |
| `camera` | `CameraFrame \| None` | head RGB-D |
| `camera.timestamp` | float | exposure time; autonomy treats frames older than 0.5 s as missing |
| `camera.intrinsics` | fx, fy, cx, cy, width, height | from calibration (sim: from fovy) |
| `camera.T_base_camera` | 4×4 | optical → base, **including the current 2-DOF head joint angles** (K1 has an articulated head per Booster spec pages) |
| `camera.rgb` / `depth` | uint8 H×W×3 / float32 H×W | either may be None |
| `camera.segmentation` (+labels, provenance) | int32 H×W | sim render = `sim_privileged`; learned segmenter = `estimated` |
| `pose` | `PoseEstimate \| None` | `pose` (x, y, yaw in map), `cov` 3×3, `source`, `provenance`, `status ∈ {ok, degraded, lost}` |
| `base_twist` | (vx, vy, wz) base frame | **measured/estimated**, used for the stable-stop check (not the commanded velocity) |
| `extra` | dict | diagnostics only; the actor never reads it |

Questions for Codex:
- **Q1 (decided by Codex, 19:18Z).** The first camera/physics adapter may use sim ground-truth pose
  **only in explicit privileged diagnostic mode**. Adding noise to an exact pose does **not**
  make it deployable odometry; it stays `sim_privileged`. Actor-mode runs need real sensor-derived
  odometry or visual localization.
- **Q2 (decided).** Fixed commanded head posture for initial integration. Extrinsics come from
  the *measured* head joints via `perception/k1_camera.py`. SCAN rotates the body and the follower
  tracks it as an absolute heading.
- **Q3 (decided).** An operator floor plan is acceptable as a labeled prior. It must not carry the
  simulator's destination identity or location. Live depth obstacle updates are still required.

## Autonomy → navigation/control: `AutonomyCommand`

| Field | Notes |
| --- | --- |
| `kind` | `navigate`, `final_approach` (decelerate + stop within tolerance), `scan` (turn in place by `scan_yaw`), `hold` (stand still, keep balance), `stop` (terminal, stay stopped) |
| `issued_at`, `expires_at` | **Control must decelerate to a hold if `now > expires_at`.** Normal TTL 1 s; autonomy refreshes every tick (~5 Hz). The same `issued_at` means the same command. |
| `goal_pose` | map frame |
| `path` | map-frame waypoints, starting at the robot's current position (2D grid plan; feasibility only) |
| `max_speed` | upper bound (m/s); 0.35 normal, 0.15 degraded/final. The controller may go slower. |
| `position_tolerance`, `yaw_tolerance` | for `reached` |
| `reason`, `state`, `selected_by` | logging and evaluation attribution (`executive` / `vla` / `baseline`) |

### Velocity bridge (new, implemented)

The official K1 locomotion policy found by Codex takes a velocity command. `navigation/follower.py`
(`PathFollower.step(cmd, pose_estimate, now, dt) → (vx, vy, wz)`) turns the command above into a
bounded, acceleration-limited base velocity:

- profile `v ≤ min(max_speed, √(2·a·remaining))`, so it decelerates to zero at the goal;
- HOLD / STOP / expired commands ramp down to zero (never a step);
- FINAL_APPROACH uses a lower acceleration (0.15 m/s²) for tray stability.

Limits are placeholders until measured on a loaded K1.

- **Q4 (decided).** The follower runs locally at 50 Hz, upstream of Codex's single command arbiter.
  No HTTP or VLA inference may block that loop.

## Control → autonomy: `ControlFeedback`

| Field | Notes |
| --- | --- |
| `timestamp`, `command_issued_at` | which command this refers to |
| `status` | `running`, `reached`, `blocked` (local obstacle / foothold check failed), `failed` (fall, balance or payload alarm) |
| `blocked_at` | map xy of the obstacle point, if known |
| `info` | e.g. tray tilt **estimate with provenance**. Sim contact forces must be marked `sim_privileged`. |

Autonomy also detects goal arrival from the pose estimate, so a lost `reached` message or a
VLA-driven approach doesn't stall the task.

## Task and outcome

- `DeliveryTask(instruction, destination: DestinationSpec, issued_at, time_limit_s)`, where
  `DestinationSpec(category, attributes, region_hint)` comes from `autonomy.grounding.parse_instruction`.
- `Region(name, center, radius, tags)` holds operator annotations; they are a **search prior only**,
  never the destination location.
- `Outcome ∈ {delivered, destination_not_found, ambiguous_destination, no_path, localization_lost,
  sensor_timeout, control_failure, timeout}`. Every terminal path emits `STOP` + an outcome +
  the executive event log.
- **Q5 (decided).** Current stop thresholds stay **provisional** (0.2 m, 0.35 rad, 1.5 s at
  ≤ 0.03 m/s). A versioned integrated protocol is frozen before task evaluation; unloaded walk
  diagnostics don't validate tray tolerances.

## Evaluation-only signals (never actor inputs)

Ground-truth robot pose, object ids/poses, rendered masks, table identity, contact forces,
payload ground-truth pose, success markers.

## Reset semantics

One `DeliveryExecutive` per task. `SceneMemory` may be passed across tasks within an episode
(long-term memory); the stale-memory test covers this. The sim reset should create a fresh memory
unless the experiment explicitly tests memory carry-over (label it).
