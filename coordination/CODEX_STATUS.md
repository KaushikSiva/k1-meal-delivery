# Codex status

Updated (UTC): 2026-10-17T21:30:42.704753+00:00
State: idle after checkpoint; goal remains active
Task: preserve real PPO training, matched failed carrying comparison, and deployment export.

Claimed paths: sim/k1_payload.py; sim/k1_payload.json; sim/k1_batch_policy.py; sim/run_k1_isaac.py; training/; deployment/export_residual.py; evaluation/plot_carrying_training.py; tests/sim/test_k1_payload.py; tests/sim/test_k1_batch_policy.py; tests/sim/test_ppo_core.py; tests/sim/test_residual_export.py; tools/remote_k1_train.sh; tools/remote_k1_walk.sh; README.md; .gitignore; experiments/codex-20261017T2043-k1-loaded-baseline/; experiments/codex-20261017T2047-ppo-pilot/; experiments/codex-20261017T2054-ppo-training/; experiments/codex-20261017T2055-ppo-cafe-evaluation/; coordination/CODEX_*.md.

Evidence: f433cb3 pushed corrected19.666kg unloaded Isaac walking/RGB-D + exact CL5 review. Supported torso fixture0.95kg plus free box0.8kg/drink0.5kg baseline dropped drink6.442s/1.24631m. PPO01 pilot1024transitions/eightupdates. PPO02 real32env training completed204800transitions/1600optimizerupdates/100iterations in293.295s;663episodes (449drops,214timeouts,0falls). Actor/critic weight changes independently verified; official base weights unchanged. No VLA fine-tuning. CPU TorchScript export matched32inputs exactly, not hardware validation.

Matched development evaluation: final PPO02 checkpoint still dropped drink12.126s/3.22968m; bodytilt4.003deg. Both baseline/candidate failed; one pair cannot establish repeatable improvement. Twelve evidence hashes verified;303video frames25fps/12.12s;606trajectory samples50Hz. Final6ms absent from sampled recordings. Fixed evaluator camera loses robot late in run; head camera continues. Need wider view and repeats. Training curves plot every actual iteration.

Validation: six new tests passed (payload mass/placement2, batched upstream equivalence1, PPO termination/update2, export1). Earlier capture/bridge tests passed. Initial/final pilot/main weights and export retained in ignored local runs/brev-k1-20261017/trained-weights/, hashes verified; remote originals retained. README has current real images/results/architecture.

GPU: no job running after completed evaluation. Keep authorized L40S k1-isaac-check-20261017 available through17:15–18:30PDT demo. $1.74/hour, user authorized5–6h; no shutdown timer. Runtime has documented Starlette metadata conflict, not a clean pipcheck.

Next: commit/push reviewed owned paths, repeat baseline/candidate with wider camera, investigate drink stability and integrate non-privileged telemetry/localization. Full goal remains active/incomplete. Hardware/operator absent; simulation work not blocked.
Last teammate update read: Claude20:43 localization freeze and20:47 CL6 showcase. Requested correction to generic-attribute identity merging and exact-goal shortcut checks. Those live/frozen teammate changes excluded from this checkpoint; root README uses already published evidence and own current results.

Turn outcome: progress, not complete or blocked.29e8727 committed; push verified to origin/main. No background heartbeat or shutdown timer. Nextactive turn resumes carrying evaluation/localization integration.

Newturn: previous classifiedprogress (actualtraining/eval/checkpoint29e8727pushed). Claim sim/run_k1_isaac.py, tools/remote_k1_pair.sh, experiments/codex-20261017T2110-wide-carrying-repeat/ for repeat with wider evaluator view. Also claim contracts/robot_telemetry.py, sim/k1_imu.py, tests/sim/test_k1_imu.py for raw bodygyro/joint telemetry and integrated relativeyaw without privileged position/yaw. ReadcurrentClaudehandoff; memory/grounding editslive, no takeover.

Gyrotelemetry3tests passed, including nativeMuJoCosensor andpoisonedrootpose; proposalhandedtoClaude. Claim sim/check_k1_imu.py and experiments/codex-20261017T2115-k1-gyro-turn/ for actual unchangedactor turning diagnostic with relativeheading error evaluated separately. Widepairjoblaunched, pollingnext.

Widepaircompletedexactsamebaseline6.442s/candidate12.126sdrop. Gyro20srealturnFAILED2.3535raddriftat50Hz; investigating500Hzsamplingbeforeintegration. Claim experiments/codex-20261017T2118-k1-gyro-500hz/ andpreserve50Hznegative.

Claim experiments/codex-20261017T2117-k1-gyro-rate-comparison/ for same-trajectory500Hzvs50Hz estimator comparison.500Hzfirsttrial error0.03044rad vs50Hz2.3535rad; verifyaliasingonidenticaltrajectorybeforehandoffclaim.

Claim sim/k1_payload_cupholder.json, sim/k1_payload.py, sim/run_k1_isaac.py, tests/sim/test_k1_payload.py, tools/remote_k1_holder.sh, experiments/codex-20261017T2120-cupholder-baseline/ for explicitnewfixture ablation: four0.02kgcupholderwalls aroundstillfree drink. Existingv1config/evidenceunchanged. Rununchangedactorfirst; doNOTattributeholderbenefittoPPO.

Claim deployment/k1_leg_estimator.py and tests/sim/test_k1_leg_estimator.py for joint/gyro-only contact-assumption leg velocity and baseheight estimates. No simulator rootpose/velocity/contactinputs. This closes cameraextrinsic/localizer inputs, with explicitlyprovisionalno-slip/lowest-foot assumptions and measured errors beforeuse.

Claim experiments/codex-20261017T2122-k1-leg-walk/ and experiments/codex-20261017T2122-k1-leg-turn/ for actual encoder/gyro-only legestimator vsheldseparate evaluationtruth. Sharedtelemetrytypealreadyproposed; leginputsfitit.

Holderv2baseline15scomplete/no drops,2.969m,box/payloadshift.08419m>.04limit =>stabilityFAIL; finalspeed.00958m/s. Claim experiments/codex-20261017T2124-cupholder-ppo-transfer/ for unchangedPPO02 evaluatedsamev2fixture, plus experiments/codex-20261017T2124-k1-leg-500hz/ for fullratelegintegration.20swalklegheightRMSE.00240m but50Hzvelocityintegrationdrifts2.06m, notready; preservefailure.

Claim docs/hardware/k1-appearance-research.json and training/research/smolvla-discovery.json for official-source research viaYou.com. CL7 fourpaths explicitlyunfrozenforClaude; noownedit. RepoPUBLIC verifiedafterreportedexplicituserchoice.

Current task: verify/archive cupholder matched results and telemetry failures; answer user that residual PPO ran but VLA did not. Read Claude21:27:56 handoff; CL7 frozen, gyro integration ongoing. Holder PPO02 transfer completed15s/3.55766m/no drops/3.311cm maxpayloadshift; provisional stability PASS, one scripted trial. Claimed reports in previously declared experiment directories; .gitignore raw IMU/leg recordings.

Holder verification complete:14 hashes each,750 trajectory samples and375frames/15seconds per video, three payload tests pass. Preparing owned carrying checkpoint only; gyro/leg and Claude changes remain unstaged for separate review.

Turn outcome: progress. User training-status question answered: actual new residual PPO trained; VLA not trained. Carrying reports/artifact checks complete. Next active work: review telemetry failures/localizer integration, repeated loaded trials, VLA feasibility and authorized artifact-storage request. No shutdown timer or unattended heartbeat. L40S retained through demo as authorized.
