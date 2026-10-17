# Codex status

Updated (UTC): 2026-10-17T23:35:00.822344+00:00
State: working — integrating hand carry with sensor-guided navigation
Task: physically supported tray with realistic pizza/Coke in the café; continue the end-to-end goal.

## Claims

Codex-owned simulation/control/training/evaluation paths per OWNERSHIP.md.
Current exact paths: sim/k1_hand_isaac.py, sim/run_k1_hand_carry_isaac.py,
sim/README.md, tools/remote_hand_carry.sh, README.md,
experiments/codex-20261017T2305-hand-carry-isaac/,
coordination/CODEX_STATUS.md, coordination/CODEX_LOG.md, coordination/CODEX_HANDOFF.md.
Earlier hand/VLA/GR00T/visual source claims are committed in ffed5dc.

## Actual results

- MuJoCo hand-contact10: 15 s, 2.036 m, 3.295 mm payload shift, 7.195° tray tilt,
  final speed0.01371 m/s, 4/2 ms longest hand-contact loss. No drop/fall or
  other robot support. Free tray with real physical hand seats and cup holder.
- Isaac café03: 15 s, 2.193 m, 8.038 mm shift, 4.369° tray tilt, final speed
  0.01850 m/s, 6 ms longest hand-contact loss, 7.391 Nm max arm torque/14 Nm.
  No drop/fall/non-hand robot support. All23 robot-body contact filters measured.
- Isaac04 close tracking view: identical root and payload/contact CSVs to03.
  Both cameras in each run are continuous375 frames/25 fps/15 s. All14
  downloaded artifacts per run hash-verified; all four hand-specific source
  snapshots independently matched. Actual rendered closeup/final frames viewed.
- Hand controller is frozen walking actor plus torque-limited arm PD and
  model gravity/load feedforward. No VLA or old torso-trained PPO residual.
  Nominal arm observation ablation is explicit. No body pose replay/weld/bracket.
- SmolVLA200 actual updates; matched closed-loop comparison executive2/4,
  SmolVLA2/4. No overall improvement. Translation drift still limits navigation.
- GR00T20 real updates; frozen hashes unchanged, trainable hashes changed;
  strict saved-shard reload produced finite[1,10,5] in0.3995 s. No GR00T
  closed-loop result yet. Live W&B run logged; PPO/Smol historical exports complete.
- Eight focused hand-gravity/payload/VLA arbitration tests pass. Failed launcher,
  import, physics tuning and dependency attempts retained in reports/artifacts.

## Handoff and integration

ffed5dc pushed origin/main. Isaac evidence checkpoint d426607 committed; push verified.
Claude's75.1 s demo update read23:06 UTC; hand-carry café footage supplied through
CODEX_HANDOFF. Claude owns localization tracking-scale WIP; do not stage it.
Ready films: experiments/codex-20261017T2305-hand-carry-isaac/attempt04/evaluator.mp4
(close), attempt03/evaluator.mp4 (wide), corresponding robot_camera.mp4 files.
No Claude-owned files staged.

## Remaining

Integrated camera-guided loaded delivery, robust varied navigation, learned
hand-carry control, GR00T comparison, object storage and hardware verification
remain unfinished. Goal active, not complete. Keep the authorized L40S available
through demo17:15–18:30 PDT; no shutdown timer. No current GPU job after04.

Previous goal turn: progress (d426607 published, actual Isaac03/04 free hand-contact carry verified). Read Claude23:07:53 café-demo update. Claim sim/k1_hand_controller.py, sim/run_k1_sensor_navigation.py, tests/sim/test_hand_controller.py, evaluation/LOADED_NAV_PROTOCOL.json, experiments/codex-20261017T2310-loaded-navigation/ and tools/remote_loaded_navigation.sh. First integrate stable committed navigation (snapshot HEAD), no Claude WIP imports, with free-tray physics and explicit loaded scoring.

Loaded-nav01 stopped ambiguous_destination at2.2s (plus2ssettle): pizza top became table#0 nearx0.32m; true table#1 near3.79m. No movement/drop/roomcontact. Claim deployment/carrying_depth_filter.py and tests/sim/test_carrying_depth_filter.py. Use known operator-configured trunk-frame carrying envelope and head-encoder camera extrinsics; mark only measured depth points within envelope unknown. Preserve raw depth/RGB, no segmentation/GT labels or hidden object state. Explicit opt-in trial02; source snapshot locks committed navigation.

Read Claude23:11:12CL12 direct user request: longerGR00T300–500updates withvalidation25stepcurve, freshloadednavigation. Claim training/finetune_groot_curve.py, training/GROOT_CURVE_PROTOCOL.json, tools/remote_groot_curve.sh, experiments/codex-20261017T2320-groot-curve/. L40S idle0MiB,27GBfree. Preparing fixedvalidationwithtrain-onlynormalization beforelaunch. Nav02selfmaskfix removespizzaambiguity butfailsdrift/no_path/drop24.8s,99roomcontactsteps; degraded0.15m/scommandsbelowwalkingdeadbandexplainfalseodometry. Claim deployment/k1_carry_commands.py and tests/sim/test_carry_commands.py for a conservative unsupported-command hold (neverraisesrequested speed), leaving executive uncertainty cap intact.

Loaded03 (guard+WIP snapshot) alsofailed; earlybothXYunconstrained followedweakmatchandbodydriftunderturning. No loadednavigationpass. GR00Tcurve01failedvalidationstatsmetadata preflight (zero updates);02 createsrequiredmetadata butreusestrainingprocessor unchanged. Continuingcameraorientationobservabilitydiagnostic; control and rawdepth evidence preserved.

Loaded-nav04 delivered at22.8s plus2ssettle: finalxy[2.9502,-.0763], finalspeed0.000513m/s, maxXYerror7.148cm, no roomcontact/drop/fall/nonhand support. Payloadshift3.801mm, traytilt5.065°, handloss4/2ms, torque8.211Nm/14. Usesheadpitch−.2rad and fixedprediction scale.5 based on prior straightcarry~.19m/s actual vs.4 commanded, no onlineGT. WIPsnapshot localizer retainedbutfixedscaleoverridesonlineestimate. Source frozen perrun; development tuning, notindependentreliabilityclaim. GR00Tcurve02running genuineupdates, val25computed.

Loaded05 repeats04 with committed localizer (fixedscale bypassesWIPonlineestimation) and25fpsfollowing/evaluator+head recording; perception remains5Hz. This testsreproducibility without incompleteClaude code. GR00Tcurve02 reached250updates; fixedvalidation is nonmonotonic, noimprovementclaim. Claim evaluation/plot_groot_training.py for raw curves plus clearlylabeledtrain smoothing; no inventedtrend.

Claim evaluation/score_loaded_navigation.py for independent physical/nav acceptance. Loaded05 completed with committed localizer and identical trajectory/contactCSV to04 (verify next),621frames25fps covering0–24.8s; nodrop/contact. Higher-fps capture is a deterministic repeat, not a second independentrobustness trial.

Loaded05 independentlypassedall15nav/loadgates; physicaltrajectory/contactCSV byteidenticalto04, committedlocalizer,621framesat25fps. All5attemptartifacthasheschecked and05source snapshots preserved. 9focusedtests passed. GR00Tcurve02exit0,500actualupdates,trainablechanged/frozenunchanged,335.08swall; validation1.76469→2.45072(worse). Reload01live; duplicatecheckpointshards beinghashverified/hardlinkedto recoverdisk, bytespreserved. Compactmetricsarchive downloading. Source/curve/navreportscheckpointnext.

Previous turn: progress (verified PUBLIC GitHub visibility and actual Crusoe use for submission). Resuming CL12 publication. Claim evaluation/plot_groot_training.py, training/finetune_groot_curve.py, experiments/codex-20261017T2320-groot-curve/REPORT.md, README.md and sim/README.md. Curve02 verified 500 updates and strict reload; 20 training log entries missing because validation logging clears should_log. Preserve gaps and fix future logger; no invented losses. Loaded05 all15 gates passed; reviewing video decode and publishing source/evidence checkpoint. Read Claude handoff through23:11:12. No current known GPU job; checking live state.

Curve02 honestgraph generated/reviewed, 480lossrecords and21validationpoints; strictreloadfinite. Loaded05bothfilms decoded621frames25fps24.84s. Claim curve03run/report subdir andtools/remote_groot_curve.sh. L40S liveidle,15GBfree. New500same-seedrepeat will preserve pendingtraininglogs and savefinalcheckpointonce (officialexperiment.run), no model/trainingconfig tuning; previousnegative result retained.

Evidence correction: score.json contains14individual boolean checks, allpassed; earlier15count included aggregatepass and mustnot be repeated. Focusedverificationrerun initiallyhadwrongtestfilename(no testsran); correctedfilename test_hand_carry.py. GR00T03livePID146012,38.9GB GPU,step25seen. Preparing immutableloaded-navigationvaried-start protocol with samecontroller andcommittedlocalizer.
