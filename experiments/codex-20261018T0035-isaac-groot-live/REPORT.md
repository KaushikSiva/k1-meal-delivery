# GR00T in live Isaac: two short previews, longer-run failure

The user requested two short live GR00T runs and restoration of missing controls/robot view. Both previews ran actual PhysX steps in Isaac Sim 5.1 on the existing L40S, using live head RGB-D and the audited 500-update GR00T checkpoint `groot-c788024b6205`. Its bounded proposals reached the baseline walking controller; hand PPO and SmolVLA were not active.

| Run | Simulated duration | GR00T calls | VLA-selected control ticks | Inference errors | Intervention |
| --- | ---: | ---: | ---: | ---: | --- |
| Longer first transfer | 9.284 s | 13 | 271 | 0 | Automatically paused after root height fell below 0.25 m |
| Short preview 1 | 4.24 s | 4 | 82 | 0 | Operator/browser Pause, then Reset |
| Short preview 2 | 4.16 s | 4 | 78 | 0 | Operator/browser Pause, then Reset |

**Neither short preview establishes successful delivery or stable stopping.** Both include two seconds of settling. Reset is an explicit simulator intervention; Pause freezes physics rather than demonstrating a physical stop. Both short runs remain in executive search. The first longer run drifted backward during turning and fell; the negative trace is retained. No robustness or model improvement claim.

The browser showed the controls hidden and camera aimed away before repair. The restored panel reopens after closing; Reset restores the robot and camera; Restore robot view is an explicit button; a detected fall produces a visible message. Browser screenshots verify the robot and panel are visible. After both previews, state JSON verifies step 0, paused, GR00T selected, and initial robot/payload poses. One UI limitation remains: the displayed call counter retains the previous run until the next control tick, although reset JSON counters are correctly zero.

Four focused sensor-boundary/joint-mapping tests passed; compilation passed. These are software checks. Actor observations use head RGB-D, joint encoders, emulated noisy body gyro, estimated pose, and an operator-supplied conservative floor plan/initial pose. True root/tray positions in live_state.json are evaluation/UI-only. Source snapshots describe the repaired preview runtime; the earlier failed-run source differs in view/reset behavior. Raw camera NPZ files stay in ignored local trace archives and on the VM.

Runtime: `/home/ubuntu/workspace/k1-runtime/live-desktop-01/scene-20261018T003257`, GUI PID182287 at verification. Original failure: `scene-20261018T002237`. Live link is local to the Mac SSH tunnel: http://localhost:16080/vnc.html?autoconnect=true&resize=scale .
