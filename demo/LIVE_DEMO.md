# Live demo: presenter cheat-sheet

## A. Live MuJoCo on this Mac (ready, verified)
```
cd ~/workspace/k1-meal-delivery
sim/.venv/bin/mjpython demo/live_mujoco.py              # real time, ~25 s to DELIVERED
sim/.venv/bin/mjpython demo/live_mujoco.py --speed 2    # 2x
```
- An interactive MuJoCo window opens. Left-drag orbits, right-drag pans, scroll zooms; the camera
  follows the robot.
- What it is:
  - the official K1 walking policy carries a **free tray in its hands** (box + sealed can, real
    contact physics);
  - it navigates with **only its own sensors** (head camera + gyro + joints; no markers, no
    simulator pose) to the table, stops and settles;
  - Codex's loaded05 configuration, unchanged.
- Verified run: **DELIVERED**, max localization error 7.1 cm. The terminal prints the full
  manifest at the end.
- Honest caption: MuJoCo simulation, first development pass, no PPO/VLA active in this run.

## B. Live Isaac Sim on the Brev L40S (Codex) — READY (verified 2026-10-18 00:10Z)
- Codex is starting the Isaac GUI on instance `k1-isaac-check-20261017` (ID `opqm34emo`) behind an
  SSH tunnel.
- Open (SSH tunnel must be up; Codex-run): http://localhost:16080/vnc.html?autoconnect=true&resize=scale
  (Start / Pause / Reset; live PhysX hand contacts, not a replay).

- Tableside panel: Start/Resume, Pause, Reset, follow camera. Verified: Start ran 900 real physics steps, Pause held, Reset returned to step 0. Baseline hand-contact physics, not PPO/VLA, not a replay. Details: docs/hardware/ISAAC_LIVE.md
