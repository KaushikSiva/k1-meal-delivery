# Codex status

Updated (UTC): 2026-10-17T20:40:55.982580+00:00
State: working
Task: checkpoint actual café RGB-D, K1 import failures and corrected unloaded Isaac walking; then supported tray and PPO carrying adaptation.

Claimed paths: sim/; tests/sim/; tools/remote_*.sh; training/; experiments/codex-*; coordination/CODEX_*.md; .gitignore. Exact next additions: sim/k1_payload.py, sim/k1_payload.json, tests/sim/test_k1_payload.py; extend sim/run_k1_isaac.py and tools/remote_k1_walk.sh for loaded baseline. No Claude WIP edits.

Evidence: prior6600726 pushed. Café6RGB-D captures verified;5geometry tests passed. Official actor bridge equivalence test passed. Walk01/02 failed before actor; preserved. Walk03 completed but19.666kg source imported as21.666kg; preserved as invalid nominal baseline. Walk04 merges empty fixed links: actual19.666kg,15s,750actor steps,2.91964m forward,4.36846deg peak tilt,no fall. Both videos375frames/15s,10artifacthashes checked; head view visually correct. No loaded run or PPO/VLA updates yet.

Budget: one Crusoe L40S k1-isaac-check-20261017, $1.74/hour, authorized5–6h including17:15–18:30PDT. No shutdown timer. VM retained. Runtime IsaacSim5.1/IsaacLab2.3.2/torch2.7cu128; documented Starlette metadata conflict. No active GPU job after walk04.

Blockers: no physical K1/operator; no blocker to simulation. Full end-to-end goal incomplete.
Next: commit reviewed checkpoint, attach documented nonzero-mass supported tray and free payload, run unchanged-policy baseline, then actual PPO.
Last teammate read: Claude20:24:26Z CL5 eleven paths frozen and independently verified; localization WIP with failing drift fixture. Other live autonomy changes excluded from staging.
