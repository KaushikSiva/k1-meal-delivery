# Codex status

Updated (UTC): 2026-10-17T19:29:28+00:00

State: working

Task: integrate reviewed baseline/autonomy fixes and authenticate user-supplied Brev access; prepare camera integration.

Claimed paths: sim/; evaluation/; tests/evaluation/; tools/fetch_upstreams.py; tools/brev_budget_guard.py; tests/integration/test_brev_budget_guard.py; tests/sim/; tests/integration/; experiments/codex-20261017T1902-k1-walk-baseline/REPORT.md; new experiments/codex-* runs; README.md; docs/RESOURCES.md; docs/hardware/; coordination/CODEX_*.md. Existing ownership allocation is unchanged.

Evidence: read GOAL, OWNERSHIP, both status and handoff files and current git state. Prior baseline process is absent. All six original artifacts verified; 750 trajectory rows. Reproduction completed with exactly matching displacement 0.2802458334 m, peak tilt 3.79502798 degrees, and 375 rendered frames. Command tracking appears poor and requires quantified diagnostic evidence. Bootstrap commit 3d30864 is the current HEAD. No files owned by Claude edited or staged.

Blockers: physical K1/operator absent. User now authorizes one $1.74/hour L40S for next 5–6 hours, including demo 17:15–18:30 PDT. Do not stop early unless clearly unused. User supplied Brev API credentials; v0.6.337 login succeeded with key saved only in native owner-only credential storage. Existing compute inventory is being checked; created k1-isaac-check-20261017 (Crusoe l40s-48gb.1x, $1.74/h); awaiting boot. Old 2-hour guard session 33528 was cancelled and returned exit 130; NO automatic shutdown remains armed. Preserve this instance for demo 2026-10-18T00:15Z–01:30Z. Reassess use at demo end rather than interrupting active work. Launch/guard records are under ignored runs/brev-k1-20261017/. No additional instance/fallback authorized.

Next: finish recorded 0/0.35/0.5 m/s command sweep; checkpoint reviewed baseline plus frozen autonomy scaffold; acknowledge Claude and prioritize reproduced integration defects. Tests: 26 autonomy, 3 real-policy/model, 5 artifact-accounting, 3 You.com client checks passed. Review reproduced degraded-localization false delivery, stale-pose acceptance and follower speed-cap bypass; sent exact findings through CODEX_HANDOFF.md.

Last teammate update read (updated freeze at 19:23Z received and regression rerun running): Claude 2026-10-17T19:15:43+00:00 supplied a frozen 26-test handoff. Review underway. Current shell python3/python3.12 lack pytest; created isolated root .venv for reproducible review, leaving sim/.venv dependencies unchanged.

Current live handle: frozen 37-file regression validation session 25424. Provisioning 53494 completed (instance opqm34emo DEPLOYING). Old guard 33528 terminal/cancelled, never restart its obsolete 2-hour deadline.
