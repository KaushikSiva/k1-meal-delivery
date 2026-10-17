# K1 MuJoCo diagnostic

The official Booster K1 TorchScript walking actor runs unchanged through its
upstream MuJoCo controller. This is an **unloaded, scripted-velocity diagnostic**.
It has no destination perception, tray, pizza, drink, learned project policy,
or hardware actuation. Isaac Sim/Isaac Lab integration remains outstanding.

Tested locally on macOS arm64, Python 3.11.13. From the repository root:

```sh
python3 tools/fetch_upstreams.py
uv venv --python 3.11.13 sim/.venv
uv pip install --python sim/.venv/bin/python -r sim/requirements-macos.lock.txt
uv pip install --python sim/.venv/bin/python --no-deps -e sim/vendor/booster_assets
sim/.venv/bin/python -m pytest tests/sim -q
sim/.venv/bin/python sim/run_k1_baseline.py --output experiments/codex-UNIQUE-k1-walk --duration 15 --speed 0.2 --render
python3 evaluation/analyze_locomotion.py experiments/codex-UNIQUE-k1-walk
```

Use an unused output directory: the runner refuses overwrites. Rendering requires
a working local OpenGL context. The dependency lock records the tested local
environment; it is not a Linux GPU lock. Do not recreate an active environment.

`upstream-lock.json` pins assets, deployment code and training source. The training
source is present for inspection; no project training has occurred. The actor's
world position and linear velocity exclusion is tested, along with velocity-command
observation mapping and finite physics stepping. IMU-equivalent orientation/angular
velocity and joints currently come directly from ideal simulator state; this does
not establish sensor noise, latency, calibration or hardware observation parity.

Each trial records a manifest, trajectory, continuous MP4 when rendering works,
and sampled evaluator-camera frames. A completed duration means the diagnostic
finished without its configured height/tilt/nonfinite termination; it is **not**
a delivery success or a calibrated fall/collision test. Video rendering failures
are recorded separately. World-position finite differences are evaluation-only.

The first 15-second trial and its exact repeat each moved 0.28025 m total with a
0.2 m/s forward command for 11 seconds. Forward-phase mean world-X velocity was
0.02791 m/s. This poor tracking needs investigation before room navigation.
See the [original report](../experiments/codex-20261017T1902-k1-walk-baseline/REPORT.md).

Recordings stay in ignored local artifact storage; manifests retain their hashes
and relative paths. They are not uploaded by a Git push. Do not delete the local
run directories until an external artifact store has been established.

## Head-camera integration adapter

`k1_observation.sensor_spec(source_xml)` adds a native camera at the official
RealSense optical link without editing vendor assets. Its 58-degree vertical FOV
and 640×480 resolution are simulation assumptions, not physical calibration.
`DiagnosticObservationAdapter(model, diagnostic=True).observe(data)` returns
RGB, metric z-depth, and explicitly privileged pose/twist/extrinsics. It emits no
instance masks or destination labels. This is geometry/render integration;
walking executive integration and deployable localization remain outstanding.

Four tests verify head articulation, optical convention, central/off-axis depth,
world-to-base velocity, and rejection on the deployable input path. The macOS
OpenGL backend reports `ARB_clip_control` unavailable, so depth precision is
limited; the tested two-meter plane was within one centimeter at both samples.
That check does not calibrate the physical camera or establish full-range accuracy.


## Free tray carried in the hands

The explicit hand-contact baseline has separate evidence from the older torso
fixture and PPO experiments. All three payload bodies are free, and the original
hand collision meshes support physical underside tray seats. See the
[MuJoCo tuning report](../experiments/codex-20261017T2300-hand-carry/REPORT.md) and
[Isaac café transfer](../experiments/codex-20261017T2305-hand-carry-isaac/REPORT.md).

```sh
sim/.venv/bin/python sim/run_k1_hand_carry.py --output runs/hand-repeat-new \
  --duration 15 --speed .4 --nominal-arm-observation --handle-seats \
  --gravity-compensation --feet-on-floor
# Run on the pinned Isaac/L40S environment with MuJoCo3.16 installed for
# inverse-dynamics calculations only; PhysX integrates all motion:
.venv/bin/python sim/run_k1_hand_carry_isaac.py --output runs/hand-isaac-new \
  --duration 15 --speed .4 --tracking-evaluator
```

These are preloaded, scripted carrying diagnostics without VLA, PPO residual or
vision guidance. A sealed rigid can is modeled; there is no liquid solver.
Joint torque limits remain active. Nominal arm observations in the frozen walking
actor are an explicit ablation; the physical arms use measured encoder feedback.
The evaluation-only tracking camera reads robot position to frame the footage;
its position is not supplied to the controller. Do not actuate a physical K1 from
this diagnostic runner.
