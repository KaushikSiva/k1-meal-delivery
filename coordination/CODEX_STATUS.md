# Codex status

Updated (UTC): 2026-10-17T21:09:12.313672+00:00
State: working — checkpoint review and push
Task: preserve real PPO training, matched failed carrying comparison, and deployment export.

Claimed paths: sim/k1_payload.py; sim/k1_payload.json; sim/k1_batch_policy.py; sim/run_k1_isaac.py; training/; deployment/export_residual.py; evaluation/plot_carrying_training.py; tests/sim/test_k1_payload.py; tests/sim/test_k1_batch_policy.py; tests/sim/test_ppo_core.py; tests/sim/test_residual_export.py; tools/remote_k1_train.sh; tools/remote_k1_walk.sh; README.md; .gitignore; experiments/codex-20261017T2043-k1-loaded-baseline/; experiments/codex-20261017T2047-ppo-pilot/; experiments/codex-20261017T2054-ppo-training/; experiments/codex-20261017T2055-ppo-cafe-evaluation/; coordination/CODEX_*.md.

Evidence: f433cb3 pushed corrected19.666kg unloaded Isaac walking/RGB-D + exact CL5 review. Supported torso fixture0.95kg plus free box0.8kg/drink0.5kg baseline dropped drink6.442s/1.24631m. PPO01 pilot1024transitions/eightupdates. PPO02 real32env training completed204800transitions/1600optimizerupdates/100iterations in293.295s;663episodes (449drops,214timeouts,0falls). Actor/critic weight changes independently verified; official base weights unchanged. No VLA fine-tuning. CPU TorchScript export matched32inputs exactly, not hardware validation.

Matched development evaluation: final PPO02 checkpoint still dropped drink12.126s/3.22968m; bodytilt4.003deg. Both baseline/candidate failed; one pair cannot establish repeatable improvement. Twelve evidence hashes verified;303video frames25fps/12.12s;606trajectory samples50Hz. Final6ms absent from sampled recordings. Fixed evaluator camera loses robot late in run; head camera continues. Need wider view and repeats. Training curves plot every actual iteration.

Validation: six new tests passed (payload mass/placement2, batched upstream equivalence1, PPO termination/update2, export1). Earlier capture/bridge tests passed. Initial/final pilot/main weights and export retained in ignored local runs/brev-k1-20261017/trained-weights/, hashes verified; remote originals retained. README has current real images/results/architecture.

GPU: no job running after completed evaluation. Keep authorized L40S k1-isaac-check-20261017 available through17:15–18:30PDT demo. $1.74/hour, user authorized5–6h; no shutdown timer. Runtime has documented Starlette metadata conflict, not a clean pipcheck.

Next: commit/push reviewed owned paths, repeat baseline/candidate with wider camera, investigate drink stability and integrate non-privileged telemetry/localization. Full goal remains active/incomplete. Hardware/operator absent; simulation work not blocked.
Last teammate update read: Claude20:43 localization freeze and20:47 CL6 showcase. Requested correction to generic-attribute identity merging and exact-goal shortcut checks. Those live/frozen teammate changes excluded from this checkpoint; root README uses already published evidence and own current results.
