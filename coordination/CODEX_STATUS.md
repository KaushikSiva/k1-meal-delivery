# Codex status

Updated (UTC): 2026-10-18T00:35:35.993279+00:00
State: ready for user demo; two short GR00T Isaac previews verified.

## Current task and claims

Restored live robot/camera and hidden Tableside panel. Codex claims sim/isaac_live_session.py, sim/isaac_groot_session.py, sim/k1_isaac_hand_residual.py, sim/run_k1_hand_carry_isaac.py, related tests/sim/, tools/start_isaac_desktop.sh, docs/hardware/ISAAC_LIVE.md, README.md, own coordination, and experiments/codex-20261018T0035-isaac-groot-live/. No Claude WIP changes.

## Evidence

- Isaac GUI PID182287 and GR00T server remain live on existing L40S. Link: http://localhost:16080/vnc.html?autoconnect=true&resize=scale . Browser screenshot confirms robot, realistic payload, panel and Use GR00T button.
- Two actual short runs:4.24s/4 calls/82 accepted ticks;4.16s/4 calls/78 accepted ticks.0 inference errors. Manually paused/reset; not full deliveries or stable-stop evaluations. Final step0 paused with GR00T selected, initial root/tray restored.
- Earlier longer GR00T run fell at9.284s after13 calls/271 accepted ticks. Failure preserved; turning drift remains unresolved. GUI reset restores camera and error after falls; closed controls reopen.
- Four focused boundary/mapping tests passed; syntax passed. Optional hand-PPO bridge software-tested but NOT enabled or physically validated in Isaac. No new training.
- Earlier hand PPO matched evaluation remained3/8 vsbaseline4/8; no promotion. GR00T PNG loaded evaluation2/4vsbaseline3/4. Robust delivery and hardware validation remain unfinished.
- Minor UI limitation: reset clears actual counters but displayed GR00T counter refreshes on next control tick.

## Coordination and next action

Read Claude handoff through direct user-authorized verifier commit3a2c89e and HEAD278114a. Acknowledge live Crusoe verifier evidence now committed, replacing prior pending-credential status. Leave user's interactive scene untouched. Publish the reviewed owned integration/evidence; then investigate controller turning and GR00T transfer without claiming delivery success. VM stays available through authorized demo window; do not shut it down due pause/idle alone.
