# Codex to Claude

## Bootstrap handoff

The user explicitly wants a company project, real progress, recorded failures, VLA + RL experiments, and five-minute Markdown updates. Simulation is sufficient now; prepare for a physical K1 arriving later. No hardware is connected and no GPU budget/access is established.

Please begin your allocated autonomy paths using CLAUDE_START.md. Keep all startup work runnable without GPU or credentials where possible, and label mocks as software tests. Do not write simulation, training, evaluation, deployment or root config files.

Initial contract discussion: propose timestamped observations with source/provenance and uncertainty; semantic target memory with last-seen time; bounded local action/subgoal outputs; explicit search/relocalization states. The deployed system must not receive exact simulator poses. Codex will consolidate a shared contract after reading your proposal.

Sponsors: You.com for new real-world research, NVIDIA for simulator/training, Crusoe for GPU and experiment-agent inference. Report missing credentials and do independent work while they are unavailable.

Git policy: Codex is the sole integrator. When a change is ready, list exact stable paths and test results in CLAUDE_HANDOFF.md and freeze those paths until commit acknowledgement. Do not stage, commit or switch the shared branch.

## Resource and goal update

The platform goal is now active after the user cleared the old one. User supplied a You.com key; read YDC_API_KEY from ignored local .env without printing it. Codex is verifying the API and will provide a shared tools/you_search.py client. Do not overwrite .env or commit it. Claude's migration from unallocated startup paths was observed and acknowledged; Codex will avoid those files while migration finishes.

## 2026-10-17T18:56:39+00:00 — You.com client ready

Use `python3 tools/you_search.py 'query' --domain docs.booster.tech --count 3 --output docs/autonomy/<unique-name>.json`. It reads YDC_API_KEY from ignored .env; do not print the key. Live API verified. Results retain source provenance and are leads, not measured properties. The script refuses to overwrite output files.

Three client tests pass via `python3 -m unittest discover -s tests/integration -v`. Codex is staging only its own implementation and coordination snapshots for checkpoint 1; your draft code remains unstaged until handoff. Coordination snapshots may be committed while agents continue updating their own status files; code integration still requires a frozen ready-path handoff.

## 2026-10-17T18:57:28+00:00 — checkpoint published

Bootstrap commit `3d30864` is pushed to private origin/main. Your draft implementation remains uncommitted pending your handoff. Goal is active. You.com client is available now. Next Codex task is the official K1 simulator/checkpoint audit and evidence tooling; no ownership change.

## Simulation work claim

Codex is inspecting official Booster revisions and baseline assets, then preparing a CPU MuJoCo smoke check under sim/ and tests/sim/. This is an additional real-asset check before the GPU Isaac Sim baseline, not a replacement for training or camera-guided delivery. Claude's autonomy paths remain untouched.

## 2026-10-17T19:00:17+00:00 — baseline policy found

Official booster_deploy at 7bb1462e2ac742eba5c01659b815e2e99fbe617f includes tasks/locomotion/robots/k1/models/k1_walk.pt (about 2 MB). Codex is attempting an actual CPU MuJoCo run using the upstream controller/policy unchanged, with a headless driver. This is a scripted-velocity locomotion diagnostic, not a navigation demo. Actor observations are IMU-derived orientation/angular velocity, joints, command and previous action; evaluator world pose must remain outside autonomy policy inputs.

The shared .venv is not being modified. Simulation dependencies are isolated in sim/.venv (Python 3.11). NVIDIA documentation surfaced through You.com excludes A100/H100 for Isaac Sim 5.1; GPU selection must account for RT cores.

## 2026-10-17T19:18:11+00:00 — successor Codex review and integration decisions

I have taken over the Codex role in the same checkout. Original MuJoCo run audited and reproduced exactly: 15 s unloaded scripted diagnostic; 0.28025 m total forward displacement, peak tilt 3.795 degrees, 375 frames. This is poor command tracking (mean world-X velocity 0.02791 m/s during the 0.2 m/s forward phase), not delivery evidence. sim/vendor sources are clean and match pinned commits.

Read your frozen handoff at 19:15:43. Reviewing for a software-only checkpoint; no commit acknowledgement yet. Please keep frozen paths frozen until the checkpoint acknowledgement below. The root shell's python3 and python3.12 lack pytest; created isolated root .venv with numpy 2.4.6 and pytest 9.1.1; use `.venv/bin/python -m pytest tests/autonomy -q -p no:cacheprovider` for reproducibility.

Reproduced integration blockers to prioritize after acknowledgement, before detector/OCR work:
- Full executive `step` with state SETTLE, dwell already satisfied, fresh target, zero twist and DEGRADED pose (sigma .25 m) returns DELIVERED. `_settle` ignores degraded. Reset dwell and forbid success across uncertainty or sensor interruptions.
- `_sensors_ok` accepts a pose timestamp -100 at observation time 2 with a fresh camera. Validate pose age, camera/pose future times, finite data and monotonic update time. Missing snapshots need an independent clock to reach timeout; adapters can pass timestamped empty Observation every tick.
- PathFollower NAVIGATE to (-.1,.1) with max_speed=0 produces [-.1,.05,0] after 100 steps: reverse and lateral corrections bypass the cap. Bound planar norm, not just positive vx; specify deceleration semantics on a cap reduction. Docstring claims jerk limitation, but current code only limits acceleration.

Contract decisions Q1–Q5:
1. First camera/physics adapter may use sim ground truth ONLY in explicit privileged diagnostic mode. Adding noise to exact pose does not establish deployable odometry; keep it privileged. Actor mode needs actual sensor-derived odometry/visual localization.
2. Fixed commanded head posture for initial integration; compute camera extrinsics from measured head joints. Body SCAN at control rate; relative scan yaw must become a tracked heading and stop when reached (current follower treats it as constant angular velocity).
3. Operator floor plan is acceptable as a labeled prior; do not pass simulator destination identity/location through it. Live depth obstacle updates remain required.
4. Follower runs locally at 50 Hz before Codex's single command arbiter; no HTTP inference may block that loop.
5. Keep existing stop thresholds labeled provisional. Freeze a versioned integrated protocol before task evaluation; unloaded walk diagnostics do not validate tray tolerances.

Codex continues baseline evidence/reproducibility and integration preparation within owned paths.

## 2026-10-17T19:21:17+00:00 — CL-1 approved; unfreeze for review fixes

Please apply your tested patch now to autonomy/executive.py, navigation/follower.py, tests/autonomy/test_follower.py and tests/autonomy/test_scenarios.py. Also correct the acknowledged provenance wording in docs/autonomy/CONTRACTS.md and the VLA data spec: memory/state features derived from privileged masks/labels are still privileged even if the raw camera image is deployable. Freeze the updated exact files and send their hashes/test results when ready. I have not staged or committed any Claude code yet and will wait for the updated freeze before integrating.

Camera addendum acknowledged for inclusion after review: perception/k1_camera.py, tests/autonomy/test_k1_camera.py, docs/autonomy/research/you-k1-realsense-model.json. I will verify FK against the pinned sim environment.

Command sweep is complete: 0/.35/.5 m/s commands yielded -.00737/2.59598/4.57584 m net displacement in 15 s; larger-command runs have .0767/.1157 m/s RMS world-XY speed during the 2 s stop phase. Do not infer loaded control limits or raise speed floors from this. Reports under experiments/codex-20261017T191921Z-command-tracking/.

## 2026-10-17T19:24:41+00:00 — one follower transition regression before staging

Updated 37-file freeze received; full suite rerun underway. Camera FK independently checked against pinned MuJoCo 3.16.0 (all six camera/head-pose combinations + optical direction pass).

One additional reproduced speed-cap issue: per-axis acceleration clipping can leave the speed ball when changing direction. With follower.v=[.245,.245,0] (norm .34648), `_track` target [.34,.05,0] (norm .34366), cap .35, dt .02, after 20 calls planar norm is .369628. Both endpoints obey the cap, but componentwise clipping does not interpolate between them. Please unfreeze only navigation/follower.py and tests/autonomy/test_follower.py for a vector-norm-limited acceleration step (or equivalent) and a direction-change regression; clear `_scan_key` in reset too, so a new episode may reuse issued_at=0. Re-freeze those two paths with hashes. Do not claim the previous exact cap-reduction time bound for arbitrary changing targets; document convergence toward the bounded target and acceleration bound. Other 35 files remain frozen.

User supplied Brev access; native login succeeded via verified official v0.6.337 binary in ignored tools/vendor. No instance provisioned and no compute budget authorized yet. No secret is in project files.

### 2026-10-17T19:25:07+00:00 — test-scope note

The root suite picked up your new unfrozen depth tests while running: 35 passed / 1 skipped / 1 failed in 56.50 s. Failure is `test_depth_obstacles.py::test_closed_loop_avoids_unmapped_obstacle_without_bumping` (BLOCKED event still present). This is outside your 37-file freeze and will be excluded from this checkpoint along with navigation/depth_obstacles.py. Please retain/fix it in your next work; I will rerun only the exact frozen tests after the follower transition fix.

## 2026-10-17T19:29:28+00:00 — Brev active, user extends through demo

Created single Crusoe L40S (48 GB VRAM), instance `k1-isaac-check-20261017`, ID `opqm34emo`, $1.74/hour. User now authorizes use over next 5–6 hours including demo 17:15–18:30 PDT. Old two-hour stop guard was cancelled (session 33528 terminal, exit 130); do not reinstate it. No automatic shutdown armed. Preserve GPU for demo; only stop early if clearly unused. Native Brev credentials only; no secrets in repository. Codex owns remote setup and compute lifecycle; do not duplicate instance creation.
