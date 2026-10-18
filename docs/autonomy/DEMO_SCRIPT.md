# Demo script — autonomy segment (Claude's part)

Demo slot: 2026-10-17 17:15–18:30 PDT. This covers the perception / memory / search / VLA-interface
segment. Codex owns simulation, control, café scene, GPU and the overall run-of-show; merge into
Codex's plan as they see fit. Every asset below already exists. Nothing here is mocked.

## Two-minute story

1. **The task** (backdrop P5, Isaac café, no robot): "Deliver the pizza and drink to table 3." The
   robot must *find* table 3 with its own camera; nobody tells it where it is.
2. **What the robot sees** (F3, then F5):
   - F3: the K1's real head-camera model reads table-number signs at 1–3 m, with zero misreads.
     When it can't read a sign, it refuses and walks closer.
   - F5: in the café, tables are found from depth geometry alone (no labels or markers): 3 of 4
     targets, 0 false tables.
3. **It walks there** (F4 + trial-B real-time videos, side by side): the official K1 walking policy,
   steered only by our autonomy stack from its head camera.
   - It starts facing away, searches, reads "3" and stops steadily at the table.
   - Show **F6**: the top-down path and command trace.
4. **Honest failure** (F6 right panel, trial C): without compensating the walking policy's low-speed
   deadband, it stalls 1.45 m short. The executive **does not** claim success. This is why a
   learned carrying controller (PPO, Codex) matters.
5. **Safety under surprises** (F1/F2 + one sentence each), all tested:
   - localization lost → stop and scan;
   - camera dropout → hold;
   - ambiguous destination → report, don't guess;
   - unmapped obstacle → reroute before contact.
6. **Architecture** (DESIGN.md diagram):
   - the VLA only *proposes* bounded local moves;
   - the executive owns safety and completion;
   - the follower turns commands into speeds for the K1 walking policy.

## Allowed claims (exact wording)

- "The official K1 walking policy, unmodified, was steered to the correct numbered table by our
  autonomy stack using the K1 head camera, in MuJoCo. This is a diagnostic with simulator pose."
- "Table numbers are read from pixels and tables are found from depth; nothing is labeled for the
  robot."
- "60 automated software tests plus 31 render-based tests pass; failures are kept and shown."

## Do NOT claim

- Real-robot or hardware results; tray or payload carrying (no payload in our trials); deployable
  localization (our closed loop on the estimated pose is a **known failure**); trained VLA or PPO
  (none trained yet); success rates (n = 1 per condition).
- Don't present the café image as a delivery: it has no robot.
- Don't play the original `evaluator.mp4` / `robot_camera.mp4` without saying "accelerated ~4×".
  Prefer the `*_realtime.mp4` versions.

## Assets (all in repo, or local + hashed)

| Slot | File |
| --- | --- |
| Backdrop | `experiments/codex-20261017T2008-cafe-lit-preview/hero.png` |
| F3 | `docs/autonomy/figures/fig3_k1_headcam_placard_reading.png` |
| F5 | `experiments/claude-20261017T2023Z-cafe-tabletop-offline/overlay_contact_sheet.png` |
| F4 | `experiments/claude-20261017T2008Z-k1-camera-autonomy-diagnostic/contact_trial-B.png` |
| Videos | same dir: `trial-B/evaluator_realtime.mp4`, `trial-B/robot_camera_realtime.mp4` (git-ignored, hashes in REPORT.md) |
| F6 | `docs/autonomy/figures/fig6_k1_trials_topdown.png` (`python3 docs/autonomy/figures/make_k1_trial_figure.py`) |
| F1/F2 | `docs/autonomy/figures/fig1_search_verify_deliver_v2.png`, `fig2_depth_obstacle_layer_v2.png` |

## Live re-run (optional, ~10 s wall time, CPU only)

```
cd ~/workspace/k1-meal-delivery
sim/.venv/bin/python experiments/claude-20261017T2008Z-k1-camera-autonomy-diagnostic/k1_autonomy_trial.py \
  --out /tmp/k1-live-$(date +%s) --max-s 120 --start-yaw 3.14159 --deadband 0.3
```

It's deterministic: it should reproduce trial B (DELIVERED at ~21.2 s sim, 0.46 m from the table
edge). Write live output outside the repo (as above) so published experiments stay immutable.

## If asked "what's next"

Deployable localization (gyro/leg odometry heading + scan matching; partially built, closed loop
not yet working), the same run in the Isaac café, tray carrying with PPO, then VLA fine-tuning on
recorded demonstrations.
