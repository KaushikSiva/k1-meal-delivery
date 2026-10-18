# Codex status

Updated (UTC): 2026-10-18T00:48:49.611456+00:00
State: completed PPO02 evidence checkpoint; live demo preserved; next stopping-control investigation.
Previous goal turn: progress (GR00T live previews and controls checkpoint d3c054e). This turn:18 physical ablations published6106975; fresh131072-transition PPO02 and28 matched trials completed.

## Claims

training/hand_carry_env.py, training/train_hand_carrying.py, sim/k1_hand_controller.py, evaluation/run_hand_turn_ablation.py, evaluation/HAND_PPO_TRANSFER_PROTOCOL.json, evaluation/plot_hand_training.py, tools/export_hand_wandb.py, README.md, own coordination, experiments/codex-20261018T0040-turn-ablation/ and experiments/codex-20261018T0045-hand-ppo02/. No edits to Claude WIP or live Isaac runtime.

## Actual evidence

- Unloaded±.18yaw turns drift0.112/0.124m; empty carrying posture1.671/1.705m; loaded1.787/1.698m. Actual-arm observation fails during settling1.56s. Zeroed arm-action history also rejected: zero-command standing drift1.220m.18 trajectory hashes verified. Both prior default baseline turning trajectories exactly reproduced400steps each;3 focused tests passed.
- PPO02 velocity_v2:131072 actual control transitions,1310720 physics steps,4096 optimizer updates,512 metrics,327 completed episodes/2 early terminations,369.276s localCPU. Fresh residual, frozen base unchanged; strict saved checkpoint reload/finite checks pass; weight deltaL2 17.291965. SHA6f0429398cdc60ccbe980e75a3dc680cacf1fd72b9ade0fd2fbe6574b691667a.
- Development16runs:baseline4/8,trained2/8. Prospective12runs:baseline2/6,trained1/6. Training pure-turn drift falls to0.110–0.241m vsbaseline1.757–1.877m, but stopping and walking regressions prevent promotion. Additional protocol frozen before training ended. All28 trajectory hashes and6 training source hashes verified.
- Private W&B export finished and verified:512 remote metric rows match all iteration/step pairs;6 artifact hashes match. Initial export stopped before run creation because SDK0.27.2 removed wandb_gql; updated read-only privacy query uses installed service API. Retry exec27859 finished successfully; receipt under PPO02 evidence. Credential passed via stdin from ignored local.env; no token in code/output/artifacts.
- Live Isaac PID182287 and GR00T157043 verified running; robot paused/reset at last read. Same browser URL http://localhost:16080/vnc.html?autoconnect=true&resize=scale . Do not restart user demo. Latest GR00T checkpoint remains500updates, baseline gait; PPO02 not deployed.

## Next action / limits

Publish reviewed owned files; W&B verification is complete. Next investigate stopping and selective use of the improved turn residual while retaining baseline forward behavior; no untested promotion. Any new gated-controller results use separate diagnostics and must be labeled development since these failures inform the design. Robust camera-guided delivery, cross-simulator learned-control success and hardware verification remain unfinished. Goal active. Last Claude handoff read through authorized direct verifier commit3a2c89e; no new handoff since.
