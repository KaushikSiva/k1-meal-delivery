# Codex status

Updated (UTC): 2026-10-17T23:08:37.245951+00:00
State: working — final hand-carry evidence review and checkpoint
Task: physically supported tray with realistic pizza/Coke in the café; continue the end-to-end goal.

## Claims

Codex-owned simulation/control/training/evaluation paths per OWNERSHIP.md.
Current exact paths: sim/k1_hand_isaac.py, sim/run_k1_hand_carry_isaac.py,
sim/README.md, tools/remote_hand_carry.sh, README.md,
experiments/codex-20261017T2305-hand-carry-isaac/,
coordination/CODEX_STATUS.md, coordination/CODEX_LOG.md, coordination/CODEX_HANDOFF.md.
Earlier hand/VLA/GR00T/visual source claims are committed in ffed5dc.

## Actual results

- MuJoCo hand-contact10: 15 s, 2.036 m, 3.295 mm payload shift, 7.195° tray tilt,
  final speed0.01371 m/s, 4/2 ms longest hand-contact loss. No drop/fall or
  other robot support. Free tray with real physical hand seats and cup holder.
- Isaac café03: 15 s, 2.193 m, 8.038 mm shift, 4.369° tray tilt, final speed
  0.01850 m/s, 6 ms longest hand-contact loss, 7.391 Nm max arm torque/14 Nm.
  No drop/fall/non-hand robot support. All23 robot-body contact filters measured.
- Isaac04 close tracking view: identical root and payload/contact CSVs to03.
  Both cameras in each run are continuous375 frames/25 fps/15 s. All14
  downloaded artifacts per run hash-verified; all four hand-specific source
  snapshots independently matched. Actual rendered closeup/final frames viewed.
- Hand controller is frozen walking actor plus torque-limited arm PD and
  model gravity/load feedforward. No VLA or old torso-trained PPO residual.
  Nominal arm observation ablation is explicit. No body pose replay/weld/bracket.
- SmolVLA200 actual updates; matched closed-loop comparison executive2/4,
  SmolVLA2/4. No overall improvement. Translation drift still limits navigation.
- GR00T20 real updates; frozen hashes unchanged, trainable hashes changed;
  strict saved-shard reload produced finite[1,10,5] in0.3995 s. No GR00T
  closed-loop result yet. Live W&B run logged; PPO/Smol historical exports complete.
- Eight focused hand-gravity/payload/VLA arbitration tests pass. Failed launcher,
  import, physics tuning and dependency attempts retained in reports/artifacts.

## Handoff and integration

ffed5dc pushed origin/main. New Isaac evidence checkpoint pending final review.
Claude's75.1 s demo update read23:06 UTC; hand-carry café footage supplied through
CODEX_HANDOFF. Claude owns localization tracking-scale WIP; do not stage it.
Ready films: experiments/codex-20261017T2305-hand-carry-isaac/attempt04/evaluator.mp4
(close), attempt03/evaluator.mp4 (wide), corresponding robot_camera.mp4 files.
No Claude-owned files staged.

## Remaining

Integrated camera-guided loaded delivery, robust varied navigation, learned
hand-carry control, GR00T comparison, object storage and hardware verification
remain unfinished. Goal active, not complete. Keep the authorized L40S available
through demo17:15–18:30 PDT; no shutdown timer. No current GPU job after04.
