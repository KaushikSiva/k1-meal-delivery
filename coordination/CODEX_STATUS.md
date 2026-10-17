# Codex status

Updated (UTC): 2026-10-17T22:14:26.266092+00:00
State: idle at verified training checkpoint
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
