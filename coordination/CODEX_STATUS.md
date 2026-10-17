# Codex status

Updated (UTC): 2026-10-17T20:15:28.285268+00:00

State: working

Task: verify the realistic café's fourth GPU render, checkpoint simulator/runtime evidence, then integrate the frozen camera-driven autonomy diagnostic.

Claimed paths: sim/; tests/sim/; tools/fetch_cafe_assets.py; tools/isaac_smoke.py; tools/remote_*.sh; docs/hardware/; docs/RESOURCES.md; .gitignore; new experiments/codex-* directories; coordination/CODEX_*.md. Existing ownership remains unchanged. Codex is sole Git integrator; Claude frozen paths are review-only until validated.

Evidence: checkpoint d3d46ff pushed. Official unloaded K1 actor reproduced in MuJoCo; command sweep exposes low-speed deadband. Real articulated head RGB-D adapter has explicit SIM_PRIVILEGED pose/extrinsic provenance; 14 camera/model tests passed. One authorized Crusoe L40S is RUNNING with driver580.178.04, IsaacSim5.1, IsaacLab2.3.2 and torch2.7+cu128. Actual physics+RGB smoke passed120steps; cube settled at z0.249998m. One upstream Starlette/FastAPI metadata conflict is documented; pipcheck is not clean. No web API service used.

Café: CC0 furniture/textures/HDRI locked by SHA256; metric USD includes six tables, eighteen chairs, colliders and staged box/drink. Three local USD checks passed. Render02 exposed red material fallback; render03 fixed textures but was underexposed. Render04 completed successfully with improved pendant/window lighting; four PNGs downloaded and hash-verified; hero/counter visually approved. All attempts preserved. No robot in this USD scene yet; no delivery or training claim.

Budget/demo: one instance k1-isaac-check-20261017 (opqm34emo), $1.74/hour, authorized for5–6h including17:15–18:30PDT (00:15–01:30UTC). Old two-hour shutdown guard cancelled, exit130. NO automatic shutdown active. Keep GPU available through demo; do not stop during integration.

Blockers: physical K1/operator absent. General visual localization, loaded control, genuine PPO/VLA training and hardware trials remain incomplete.

Next: inspect render04, write verified preview report, audit and push owned checkpoint. Review Claude's new complete freeze and meaningful regressions before integrating. No blanket staging.

Last teammate update read: Claude2026-10-17T20:12:47Z complete78-file freeze supersedes earlier mismatches. Reports A/B delivered unloaded with privileged localization/restricted placard and opt-in0.3m/s deadband compensation; C timed out. Independently ran earlier developmental autonomy suite53passed16skipped and camera/placard/tabletop31passed; current frozen set needs exact hash verification and code review.
