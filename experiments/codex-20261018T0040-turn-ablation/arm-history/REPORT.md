# Previous-action arm feature ablation: reject

Six8s physical MuJoCo runs compared unchanged nominal-arm observations with an additional explicit zeroing of eight arm previous-action features. Actual carrying-arm control and payload physics remain unchanged. No new training, VLA or navigation.

The baseline again drifted1.787/1.698m under -/+0.18rad/s yaw and stood at zero command (0.074m maximum initial settling displacement). Zeroing arm action history reduced turn drift to0.786/0.918m, still far above the0.2m diagnostic limit, and broke zero-command standing:1.220m drift and0.113m/s final speed. Reject this as a controller fix. Smaller turn drift alone is insufficient. No live deployment.

Raw trajectories remain in ignored runs/hand-turn-history-01; hashes and source snapshots are retained. All6 trajectory hashes verified. Same initial state/seed per condition: a development ablation, not a reliability estimate.
