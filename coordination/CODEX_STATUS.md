# Codex status

Updated (UTC): 2026-10-17T23:02:26.347668+00:00
State: working
Task: real sensor-derived VLA pilot, reproducible evidence, and integrated loaded delivery.

## Current claims

Continuing Codex ownership from OWNERSHIP.md. Active exact paths:
- sim/run_k1_sensor_navigation.py; training/SENSOR_DEMO_PROTOCOL.json;
  training/collect_sensor_demos.py; training/prepare_sensor_dataset.py;
  training/finetune_smolvla.py; tests/sim/test_sensor_dataset.py; .gitignore.
- tools/remote_smolvla_train.sh; tools/remote_groot_setup.sh;
  training/GR00T_FEASIBILITY.md; training/research/groot-setup-discovery.json.
- experiments/codex-20261017T2210-sensor-demo-pilot/;
  experiments/codex-20261017T2215-smolvla-training/; README.md;
  coordination/CODEX_STATUS.md; coordination/CODEX_HANDOFF.md; coordination/CODEX_LOG.md.

## Actual evidence

- PPO02: 204,800 simulator transitions, 1,600 optimizer updates. New carrying
  residual trained; official walking actor frozen. Original tray dropped drink;
  adding explicit cup holder gave one scripted 15 s / 3.56 m stability pass.
- Appearance03: actual colored K1 frame verified, 23 effective material bindings.
  Root and payload trajectories byte-identical to preceding cup-holder trial.
  Attempts01 (import traversal failure) and02 (still white) preserved.
- Sensor-only unloaded navigation: one 19 s delivered run, final true speed
  0.00124 m/s. No privileged pose or markers. Corrected tabletop detector.
- Varied teacher collection: 4 delivered / 10 attempts, 6 timeouts; one contact
  trial. All 1,791 artifacts verified. Three training episodes / 262 frames,
  one validation episode / 149 frames. Failures excluded from training but retained.
  Translation localization drift reaches 3.62 m in failed variants.
- SmolVLA custom 16-state / 5-action / head-camera GPU probe passed, with zero
  optimizer updates. Actual training attempt01 failed before updates because
  NumPy cannot hash bfloat16 directly. Raw-byte fingerprint fix checked on
  bfloat16/float16/float32. Attempt02 launched with unchanged data and 200-update budget.
- User HF access checked: gated Cosmos config HTTP200. Isolated GR00T setup01
  dependency check passed; pinned model downloads running. No GR00T training.

## Validation and integration

Tabletop regression8 tests passed, dataset provenance/chunk/normalization3 tests
passed. a9d8f62 pushed origin/main: actual colored hero, navigation report,
SmolVLA probe, exact Claude tabletop freeze. Tabletop paths now UNFROZEN by handoff.
Heading-fusion WIP and other Claude drafts remain excluded.

Last teammate update read: Claude22:04:26 handoff /22:04:33 status. They own
Gemini pointing evaluation and heading-fusion translation-scale work.

## Next and limits

Inspect SmolVLA attempt02, preserve all failures, verify actual weight changes and
frozen weights, publish pilot results. Continue GR00T compatibility after setup.
Loaded camera-guided delivery, varied robust navigation and hardware are unfinished.
Goal active; this is progress, not completion. Keep L40S available through demo
17:15–18:30 PDT under the user's $1.74/hour, 5–6-hour authorization. No shutdown timer.

Major result: SmolVLA attempt02 exited zero after 200 actual optimizer updates in20.264s. Verifying saved checkpoint and before/after offline metrics before publication. GR00Tsetup01 exited zero: pinned models downloaded, import verified, dependencies clean; still no GR00T inference/training. Sensor/dataset interface10tests pass. Claim evaluation/plot_smolvla_training.py and experiments/codex-20261017T2215-groot-setup/ for completed-evidence reports.

Claim training/verify_smolvla_checkpoint.py for strict saved-checkpoint reload and actual recorded-input inference, without optimizer updates. Independent artifact hashes already verified remotely;122parameter tensors changed,L2delta7.3128;frozen VLM hashunchanged. Validation16sampledrow normalizedactionMSE0.5953→0.1690, offlineonly.

Completed verification: training02savedcheckpoint independentlyhashchecked; strictreload matched both trainable/frozenhashes and actualvalidationRGB/state producedfinite[1,10,5],firstinference.454s. 200steps/source/datasethashesverified. GR00Tsetup01complete,metadataretrieved; noinferenceorupdates. Preparing second coherent checkpoint with all10collectionattempts, actualtraining, and dependencysetup.

Turn outcome: progress, not complete/blocked. SmolVLA200updates completed and strictreloadpassed; GR00Tsetupcomplete. No GPU job currently running. L40S retained for next work/demo as authorized. No unattended heartbeat or shutdown timer. Next active turn: bounded-adapter closed-loop comparison, GR00T modality probe, loadednavigationintegration and requested object-storage setup.

New turn classification: previous turn progress (4717fc5 pushed, actual SmolVLA200updates/checkpointreload and GR00Tdownloads). Read latestClaude22:10:38Geminihandoff. Claim deployment/smolvla_policy.py, deployment/vla_session.py, sim/run_k1_sensor_navigation.py, evaluation/VLA_CLOSED_LOOP_PROTOCOL.json, evaluation/run_vla_comparison.py, tests/sim/test_vla_session.py, tools/remote_vla_comparison.sh, experiments/codex-20261017T2230-vla-closed-loop/ for same-environment executive vs trainedVLA simulatorcomparison. Claudeownedmodulesreadonly; singlefolloweractuationowner; explicitlymodelmeasuredinferencelatencybeforeproposalavailability.

VLA single-follower wrapper and strict checkpoint inference implemented. Three meaningful tests pass: measured simulated latency, control-clock expiry despite staleexecutivetimestamp, safety-statepreemption. Frozen4configuration×2mode comparison protocol written beforeevaluation. RemoteisolatedMuJoCo/EGLsetupinprogress; hardware runtime explicitlynotclaimed.

Read Claude22:18:33CL10: userprovidedW&Bkeyinignored.envandrequestedtraininglogging. Claim tools/export_wandb_runs.py, docs/RESOURCES.md and experiments/codex-20261017T2230-wandb-export/ for explicit historical-metrics importwithprivateproject/provenance, no weights/secrets. MatchedVLAcomparison01launched afterMuJoCo3.16/EGL/pipcheckpass;37sourcefilessnapshotted.

Latest direct user request: realistic Domino’s/pizza, Coke and tray, researched through You.com. Claim sim/k1_payload_visuals.py, sim/assets/payload/, sim/research/you-dominos-packaging-20261017.json, sim/research/you-coke-can-20261017.json, tools/build_payload_textures.py, sim/run_k1_isaac.py, experiments/codex-20261017T2240-payload-realism/. Visual geometry only; preserve collision/mass proxies and verify actual rendered result and matched carrying trajectory. VLA comparison01 failed preflight: remote booster_assets Python package missing; retain failure and repair deployment for attempt02.

Payload reference research complete through You.com; official Domino’s recycling box image inspected, official Coke wordmark downloaded for referential packaging. Procedural texture/mesh shells built, validating USD bindings before actual render. No image-generated experiment evidence. Comparison02 launched with missing pinned booster_assets package initializer included.

Actual comparison02: first pair executive timeout, SmolVLA physical delivery pass (26 real calls, mean latency154ms, 520 VLA-controlled ticks); second executive timeout. This is incomplete small development comparison, no broad performance claim. Payload shell USD constructed locally with no added collision APIs; six wrapper/payload tests pass. Realism01 remote render queued after comparison to avoid GPU latency contamination. Large source copy succeeded after CLI command-size failure (no render had launched on failed command).

W&B historical export complete and locally hash-verified:100PPOiteration rows/1600updates and200Smolupdates, API-verified finished in private project. Checkpoint92ca2f2 created/pushing. Comparison02 six/eighttrials finished; one pass per mode so far, no improvement claim. Payloadrealism01 queued.

User asks “groot too?” Answered honestly: setupcomplete, noGR00Tupdatesyet. Claim training/prepare_groot_dataset.py, training/groot_k1_config.py, training/finetune_groot_pilot.py, tools/remote_groot_pilot.sh, experiments/codex-20261017T2245-groot-pilot/. Preparing official GR00T LeRobotv2 format from the same qualified training episodes, preserving validation separately, then short real training feasibility run after currentGPUjobs. Official pinned docs/source inspected.

Critical user correction: tray MUST be physically supported in both hands, no floating, real physics. Existing torso-bracket trial explicitly does not satisfy this. Claim sim/k1_hand_carry.py, sim/k1_hand_payload.json, sim/run_k1_hand_carry.py, tools/remote_hand_carry.sh, tests/sim/test_hand_carry.py and experiments/codex-20261017T2300-hand-carry/ for free-tray hand-contact setup, posture/torque/contact checks. Preserve older torso evidence; do not call prior pass hand-carry success. Realistic payloadrender01 passed and trajectoriesbyteidentical but still torso-supported. GR00Tpilot01 hit missing FFmpeg sharedlibraries beforeupdates; correcting runtime then distinctattempt02.

GR00Tpilot02completed20realupdates,1.6205Btrainable/1.5235Bfrozen; trainablehashchanged,frozenhashunchanged,peak35.88GiB,27.51strainruntime. Pilot01failedmissingFFmpeg, aptFFmpeg4.4runtimefixedandactualTorchCodec87framedecodepassed. Handcarry01preflightrenderresolutionfailure;02initial5.5cmforearm/traypenetrationejectedtrayat4ms. Fixingplacement/depth/reach before any walk claim. No torso bracket or trayweld in newhandmodel.

Hand03–05 noinitialpenetrationbutdrop~0.5s; nominalarmfeatureablationreducedrootdriftbutdidnotpreventtraytipping. Added visible physicalundersidehandseats (notwelds), alsofailed. Diagnosis: modelstartsfeet~5cmabovefloor; correctinginitialfootclearance andaddingjointtorque-limitedmodelgravity/knownloadfeedforward. Trial06running. Claim training/verify_groot_checkpoint.py for savedGR00Tshardhashcheckandrecordedvalidationinputinference; launched. FullVLAarchive1.15GBstillcopying; compactreviewarchivescreatedseparately.

Current: hand07/08 sustain real free-tray contact for8/15s, no torso or other robot support, payload shift0.69mm, max arm torque5.63Nm. Attempt08 commanded0.25m/s but did not walk (net−0.069m); diagnosing baseline tracking, not claiming carry delivery. GR00T20updates finished; reload01 failed offline Hugging Face metadata access, retrying authenticated online. Read Claude22:51:28CL11 request for15s real hand-carry café/head clips.

Claim sim/k1_hand_isaac.py and sim/run_k1_hand_carry_isaac.py for true PhysX free-tray transfer; exact physical components copied from MuJoCo, newcontactmeasurement, recordedmodel-basedjointfeedforward. Hand09actual15s/2.036m/3.3mmshift/no drop. Source snapshot archived per run from09 onward.

Claim evaluation/HAND_CARRY_PROTOCOL.json. Frozen development repetition thresholds after01–09tuning, notheldoutfinaleval. Trial10adds500Hzhandcontacttrace/longestcontactlossandper-steppeaktilt plusfollowingcamera; physicsunchanged. GR00Treload02passedactualsavedcheckpointinference0.3995s, finite[1,10,5]. CompactVLA/GROOTarchivesretrievedandextracted. Isaacphysicaltransfer01sourceuploaded,launchpending.

Hand10per-steprepeat: same2.036mtrajectory, peaktilt7.195°, longesthandcontactloss4ms/2ms;8meaningfulsupport/gravity/wrapper/payloadtestspass. PublishedMuJoCodevelopmentreportwith01–10failures/attempts. Isaac01failedlauncheruvpath;02rejectednegativecomponentnameasinvalidUSDpath;03fixesnamingonly. NoIsaaccarrysuccessyet. Stoppedstalled26minfullVLAcopy; compactcomparison/trialmanifestsretrievedandfullrawarchivepreservedremote.
