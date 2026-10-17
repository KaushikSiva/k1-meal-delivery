# Unloaded K1 walking diagnostic — codex-20261017T1902-k1-walk-baseline

Review date: 2026-10-17T19:20:01+00:00. Author: Codex.
Evidence state: simulator-tested locomotion diagnostic only. Conclusion: poor
command tracking; no delivery, payload, learned improvement or hardware claim.

## Hypothesis and exact setup

The pinned official K1 walking actor can load and step with the official MuJoCo
model/controller. No upstream policy or controller change; only a headless driver
replaces interactive velocity entry. Seed 0, default initial pose, no payload or
obstacles. Command: stand for 2 s, forward 0.2 m/s for 11 s, stop for 2 s.
This is a development diagnostic, not a held-out evaluation. Its height <0.30 m
or base tilt >60 degree early termination rules do not measure all kinds of fall.

```sh
sim/.venv/bin/python sim/run_k1_baseline.py --output experiments/codex-20261017T1902-k1-walk-baseline --duration 15 --speed 0.2 --render
python3 evaluation/analyze_locomotion.py experiments/codex-20261017T1902-k1-walk-baseline
```

The output already exists; use a new run ID to reproduce. Exact source revisions,
runner/model/checkpoint hashes and library versions are in [manifest.json](manifest.json).
All pinned repositories were verified clean in this review. The original runner
hash equals the current file; actor parameters were not trained or changed.

## Recorded outcomes

- Requested/started/completed diagnostics: 1/1/1; excluded: 0.
- Termination: `completed_requested_duration`; elapsed simulation 15.000000 s.
- Net world-X displacement: 0.280245833 m.
- Minimum base height: 0.537765 m; maximum base tilt: 3.795028 degrees.
- Forward phase: mean world-X velocity 0.027912 m/s versus commanded 0.2 m/s.
- Forward phase world-X command proxy RMSE: 0.177544 m/s.
- Stop phase RMS world-XY speed: 0.029232 m/s; net world-X drift -0.018793 m.
- Continuous evaluator-camera video: 375 frames at 25 fps, 640×480; render error: None.
- Trajectory: 750 policy-rate rows. All recorded artifact hashes/sizes verified.
- Delivery success, collisions, payload drop/stability and hardware performance: unmeasured.
- Training steps, optimizer steps and GPU spending: none; pretrained upstream actor only.

Velocities above are evaluator finite differences of world position. The trace
contains no yaw or directly measured twist, so world-X error is only a tracking
proxy and does not prove body-frame speed accuracy or stable task completion.
No confidence interval is justified by one deterministic seed. Repeating the same
seed checks reproducibility; it is not an independent reliability trial.

## Artifacts and provenance

[Manifest](manifest.json) contains the SHA-256 and byte count for `trajectory.csv`,
`trial.mp4` and the three PNG frames. The CSV and video remain in this local run
directory, excluded from Git. No remote artifact store has been configured.
The screenshots are actual evaluator-camera renders, not robot-camera observations.
The camera follows evaluator world position; this does not feed the actor.

## Failure analysis and next experiment

The run completed without the configured termination but tracks forward commands
poorly. The exact repeat yields the same trajectory hash and displacement; the
result is not transient render timing. Investigate command response at frozen
speeds 0, 0.35 and 0.5 m/s with the same untouched actor/model, then compare the
training observation/action and asset configuration. No success threshold will
be selected from those development results.
