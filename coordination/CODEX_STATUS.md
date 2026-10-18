# Codex status

Updated (UTC): 2026-10-18T00:12:39.198159+00:00
State: working — live Isaac desktop ready; publishing evidence, then carrying-control work.
Previous goal turn: progress. Implemented and verified an interactive Isaac GUI and completed a new hand-contact PPO training/evaluation.

## Current claims

Codex retains ownership from OWNERSHIP.md. Active files: sim/isaac_live_session.py,
sim/run_k1_hand_carry_isaac.py, tools/start_isaac_desktop.sh,
docs/hardware/ISAAC_LIVE.md, docs/hardware/isaac-live-desktop.png,
training/hand_carry_env.py, training/train_hand_carrying.py,
deployment/hand_residual.py, tests/sim/test_hand_residual.py,
evaluation/HAND_PPO_PROTOCOL.json, evaluation/evaluate_hand_residual.py,
evaluation/plot_hand_training.py, tools/export_hand_wandb.py,
experiments/codex-20261018T0000-hand-ppo/,
experiments/codex-20261017T2355-groot-loaded/png/,
README.md, .gitignore, coordination/OWNERSHIP.md and own coordination files.

## Verified live demo

- Browser URL: http://localhost:16080/vnc.html?autoconnect=true&resize=scale on this Mac.
- Actual Isaac Sim 5.1 café GUI on L40S, process165918. Browser screenshot verified robot, printed pizza/Coke and physical hand-supported tray.
- Browser Start advanced900 physics steps/1.8 simulated seconds; Pause held state; Reset returned step0 and initial root/payload poses. Left paused for the user. Native Start/Resume, Pause, Reset and following-camera controls. No replay, PPO or VLA active.
- Xvfb/openbox/x11vnc/noVNC services bind loopback; local16080 forwards to remote6080 through SSH. Do not restart or manipulate the user's active session without need.
- L40S remains available through17:15–18:30 PDT demo. GR00T server157043 also remains available. Last free disk7.6GB.

## New evidence

- Hand PPO01:32768 actual control transitions,327680 physics steps,1024 updates,81 completed episodes/1 early termination,77.6s CPU training. Frozen base unchanged, residual weights changed and strict reload passed.
- Matched sixteen physical runs: baseline4/8, residual3/8. Pure-turn drift worsened; trained policy not promoted. Evaluation protocol frozen before training, with actual motion and stable-stop gates.
- W&B hand-ppo-01-historical API-verified finished,128 actual metric rows and evaluation totals; all exported file hashes match local evidence.
- GR00T PNG batch2/4 vs baseline3/4; first condition physically failed despite executive delivery; second dropped. All749 recorded artifact hashes verified. Raw transport batch remains3/4 vs3/4.
- Earlier recorded Isaac baseline and camera-guided MuJoCo delivery evidence remain available; hardware unverified.

## Integration and next actions

Public HEAD before this checkpoint:d9b4c12. Commit only reviewed owned files. Never stage navigation/localization.py or other Claude WIP.
Read Claude handoffs through CL14 local demo freeze00:07:22. Acknowledged Claude ownership of agents/, tests/agents/, demo/ and verifier outputs. CL13 verifier review found fail-open completion checks; requested fixes and new tests/hashes before integration. No live Crusoe Managed Inference call yet verified.
Finish coherent evidence push, keep live GUI available, then address carrying-controller failures. Goal remains active: robust varied delivery, improved learned control and hardware validation are unfinished.
