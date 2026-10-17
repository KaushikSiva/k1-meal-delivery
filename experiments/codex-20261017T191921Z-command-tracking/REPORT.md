# K1 command-response development sweep

Author: Codex. Reviewed 2026-10-17T19:20:36+00:00.
Evidence state: simulator-tested, unloaded scripted velocities. No training.

## Hypothesis and protocol

Investigate whether the poor 0.2 m/s response is uniform across commands. Frozen
before execution in [PROTOCOL.json](PROTOCOL.json): commands 0, 0.35, 0.5 m/s,
15 seconds each (2 s stand, 11 s command, 2 s stop), same default initial pose,
seed 0, official untouched actor/model/controller. No success threshold, policy
selection or held-out evaluation. This sweep follows the already observed
0.2 m/s baseline and is explicitly development data.

Run each trial from repository root, substituting N and SPEED from the protocol:

```sh
sim/.venv/bin/python sim/run_k1_baseline.py --output experiments/codex-20261017T191921Z-command-tracking/trial-N --duration 15 --speed SPEED --render
python3 evaluation/analyze_locomotion.py experiments/codex-20261017T191921Z-command-tracking/trial-N
```

Existing outputs are immutable; reproduction needs a new run directory. Each
trial manifest records code/model/checkpoint hashes, dependencies, pinned source
revisions, exact command, platform, timing and artifact hashes. Each recorded
video is 375 frames at 25 fps; all 3 trials rendered without error. Evaluator
camera follows world position and is not a robot observation.

## Outcomes

Requested/started/completed: **3/3/3**. Excluded: **0**. All terminated with
`completed_requested_duration`. No configured height/tilt termination occurred.
This is not an exhaustive fall/contact detector; collisions are unmeasured.

| Trial | Command m/s | Net world-X m | Forward mean world-X m/s | Stop RMS world-XY m/s | Peak base tilt deg |
| --- | ---: | ---: | ---: | ---: | ---: |
| trial-0 | 0.00 | -0.0074 | 0.0001 | 0.0000 | 1.324 |
| trial-1 | 0.35 | 2.5960 | 0.2363 | 0.0767 | 4.921 |
| trial-2 | 0.50 | 4.5758 | 0.4119 | 0.1157 | 4.106 |

Audited calculations are in [SUMMARY.json](SUMMARY.json). All 750 trajectory
rows and all recorded hashes/sizes checked for each trial. Velocity uses finite
differences of evaluator world position; without a yaw trace, world-X tracking
is a proxy for body-forward tracking. Stop RMS is not a continuous dwell test.
Delivery success, destination error, payload motion/drops and hardware behavior
remain unmeasured. Zero-command balance and larger-command walking are distinct
behaviors; this sweep does not validate carrying at either speed.

## Conclusion and next experiment

The policy responds substantially more at larger commands; a uniform scale error
alone does not explain the observed response. A low-command gait transition or
training/deployment mismatch remains a hypothesis, not a diagnosed cause. Do not
raise the delivery speed floor from these observations: gentle approach and
stopping with a load are required. Next inspect training/deployment observation
and gait configuration, add yaw/body-velocity instrumentation, and evaluate low
speed deceleration with a declared tray model before controller learning.

Three seeded trials do not establish reliability or an improvement. No optimizer
steps, demonstrations, GPU hours or paid resources were used. This CPU MuJoCo
work does not complete the planned NVIDIA Isaac Sim/Isaac Lab baseline.

## Artifact storage

Each `trial-N/manifest.json` lists SHA-256 and sizes for the local `trial.mp4`,
`trajectory.csv` and real rendered PNGs. CSV/video are excluded from Git, retained
at this report's local path. No remote artifact storage exists yet. This report
preserves all attempts and does not hide infrastructure failures (none observed).
