# Presentation picture log

The user asked that we **note the pictures for a presentation**. This is a running, sourced log. Every
picture states exactly what it is evidence of, per GOAL.md: no invented images, and synthetic figures
are always labeled as synthetic. Add new entries at the bottom and never edit or remove old ones;
mark superseded pictures instead.

| # | Picture | What it shows | Evidence kind | Source / provenance |
| --- | --- | --- | --- | --- |
| P1 | `experiments/codex-20261017T191921Z-command-tracking/trial-2/frame-00250.png` | Official Booster K1 model mid-stride in MuJoCo under the official `k1_walk.pt` policy, commanded 0.5 m/s | MuJoCo scripted-velocity locomotion **diagnostic**, unloaded, not vision-guided | Codex run. Manifest: 4.58 m net displacement in 15 s, completed, peak tilt 4.1°. Checkpoint sha256 2d860167…, booster_deploy@7bb1462e |
| P2 | `experiments/codex-20261017T191921Z-command-tracking/trial-1/frame-00250.png` | Same diagnostic at 0.35 m/s | same as P1 | Codex run. 2.60 m in 15 s, peak tilt 4.9° |
| P3 | `experiments/codex-20261017T1918-k1-walk-reproduction/frame-00500.png` | K1 standing after the stop phase (0.2 m/s run) | same as P1 | Codex reproduction. Note: poor tracking at 0.2 m/s (≈0.028 m/s mean), see Codex handoff 19:18Z |
| P4 | `experiments/*/trial.mp4` (per run) | Continuous video of each diagnostic trial | same as P1 | Codex. Large media stays out of Git per policy; reference by path + hash in the manifests |
| F1 | `docs/autonomy/figures/fig1_search_verify_deliver_v2.png` (v1 kept as `*_v1_historical.png`) | Top-down: "deliver to table 3", with table 3 hidden behind a partition. The robot explores, reads table numbers on the way (rejects table 2), confirms table 3, decelerates and stops. Path colored by executive state. | **Synthetic CPU fixture**, software behavior only (point robot, perfect depth, privileged fixture detector) | Claude, `docs/autonomy/figures/make_figures.py` (deterministic, seed 0; source hashes in `FIGURES_V2_PROVENANCE.txt`) |
| F2 | `docs/autonomy/figures/fig2_depth_obstacle_layer_v2.png` (v1 kept as `*_v1_historical.png`; the v1 generator can no longer reproduce its left panel since the live layer became the default, see FIGURES_V2_PROVENANCE.txt) | Side by side: a cart missing from the floor plan. With the prior map only, the robot bumps it (1 BLOCKED contact) and replans. With the executive's own live depth obstacle layer (red = cells observed occupied), it routes around with 0 contacts. The ablation uses the executive switch `obstacle_layer=False`. | **Synthetic CPU fixture**, software behavior only | Claude, same script |
| F3 | `docs/autonomy/figures/fig3_k1_headcam_placard_reading.png` | **Robot's-eye view.** The official K1 model's head camera (MuJoCo render through Codex's `sim/k1_observation.py`) reads table-number placards at 1/2/3 m: "3" (0.85), "12" (0.99), "7" (0.99). | **Restricted placard diagnostic** (custom signs). Robot posed, not walking. Sim pose privileged. Camera 640×480 / fovy 58 assumed. Not delivery evidence. | Claude, `sim/.venv/bin/python docs/autonomy/figures/make_k1cam_figure.py`. Reader: 28/30 correct, 2 refusals, **0 misreads** over 5 numbers × 6 distances; synthetic sweep 0 misreads in 340 cases incl. rotations |
| P5 | `experiments/codex-20261017T2008-cafe-lit-preview/hero.png` | Photoreal Isaac Sim RTX café (round tables, chairs, pendant lights, window wall): the scene the demo will use | **Environment preview, no robot present**, not a delivery trial | Codex; caption/limits per that REPORT.md; Poly Haven CC0 assets |
| F4 | `experiments/claude-20261017T2008Z-k1-camera-autonomy-diagnostic/contact_trial-B.png` (+ per-trial **`evaluator_realtime.mp4` / `robot_camera_realtime.mp4`**: real-time derivatives built from exact recovered frame timestamps. The original `*.mp4` play ~4× fast and must be captioned "accelerated ~4×". Git-ignored, hashed in REPORT.md) | **Headline clip.** Official K1 walking policy in MuJoCo, steered by its own head camera: it starts facing away, turns and searches, reads table "3", walks over and passes the executive's stability check (trial B: DELIVERED at 21.2 s sim, 0.46 m from the table edge; the 2 s hold afterwards isn't in the video). Top row: evaluator view; bottom row: robot camera. | **MuJoCo privileged diagnostic**: sim pose; restricted placard; unloaded; deadband compensation on; n=1 per condition. Trial C (no compensation) **stalled**, shown honestly | Claude, `experiments/claude-20261017T2008Z-k1-camera-autonomy-diagnostic/REPORT.md` |

## Suggested slide flow

1. **Problem**: K1 carries a tray to a table it has to find by sight (GOAL.md). Backdrop: P5 café.
2. **The robot**: P1/P2, the real K1 model walking under the official policy in simulation.
   Caption it as an unloaded locomotion diagnostic.
3. **The honest gap**: P3, with the measured command-tracking numbers. This shows we measure and
   report rather than assume.
4. **What the robot sees**: F3, the K1 head camera reading table numbers. Caption: restricted
   placard diagnostic; general unmarked table grounding comes next.
5. **It walks there**: F4 + the trial-B *real-time* videos (evaluator and robot camera side by side). Show the
   trial-C stall too: honest limitation, and the reason PPO carrying control matters.
6. **Autonomy brain**: F1, finding a never-seen destination by reading table numbers, then a stable
   stop.
7. **Safety under surprises**: F2, plus the list of tested failure behaviors: localization lost →
   stop and scan; camera dropout → hold; ambiguous destination → report, don't guess.
8. **Architecture**: the diagram in docs/ARCHITECTURE.md / docs/autonomy/DESIGN.md (VLA proposes,
   executive decides, follower → walking policy).
9. **Next**: the camera→walking diagnostic exists (F4) but uses a privileged pose and placards. Next: deployable localization, run it in Codex's café scene (Isaac), payload/tray carrying with PPO, VLA data.

Caption every synthetic figure with "software fixture, not robot evidence". Caption sim frames by kind:
- P1–P3 (Codex locomotion runs): "MuJoCo diagnostic, unloaded, **scripted velocity commands**".
- F3: "MuJoCo render, posed robot, restricted placard diagnostic".
- F4 / Claude trials: "MuJoCo diagnostic, **camera-driven autonomy commands**, privileged sim pose,
  unloaded, restricted placard, deadband compensation on (trial C: off → stalled)".
- Café renders (P5): "Isaac Sim environment preview, no robot".

## Pictures we still want (once they exist; do not mock them up)

- Head-camera view from a *walking* K1 in the café scene, with detections overlaid. (Posed version
  exists: F3.)
- A top-down trajectory plot of the integrated run (data in each trial's `trajectory.csv`). Same run in Codex's realistic café scene (Isaac).
- Tray-carrying frames (payload present) once the carrying controller exists.
- Real K1 photos/video when hardware arrives, with trial IDs.

## Scene intent (user steering, 2026-10-17 ~19:45Z, via Codex)

The user wants **as realistic a café scene as possible**, both for the company goal and to compete
in the hackathon. Codex owns the café assets, layout, lighting and payload under sim/. For the
presentation:
- show both an **evaluator view** (third-person) and the **robot's own camera**, side by side;
- no scripted-success substitution: every delivery clip must come from a real closed-loop run
  with its trial ID;
- placards appear only as ordinary scene content (table-number stands are common in cafés) and are
  labeled as a restricted diagnostic. Unmarked table grounding (geometry from depth) is the general
  path (`perception/tabletop.py`, done). Any run on Codex's diagnostic adapter is **privileged**
  end to end (sim pose/extrinsics), even though the perception itself only uses RGB-D.
