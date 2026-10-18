# Codex work log

## Bootstrap — 2026-10-17

- User requested a dedicated project folder, private GitHub checkpoints, nonoverlapping Codex/Claude collaboration and Markdown updates at least every five minutes of active work.
- Created local repository and private remote `KaushikSiva/k1-meal-delivery`.
- Platform goal creation failed because an unfinished Kodambakkam goal exists. User authorized pausing it; pause succeeded. No false completion was recorded.
- No simulation, training, physical trial or success-rate evidence exists yet.

## 2026-10-17T18:56:39+00:00 — verified API and initial environment

- User cleared old goal and activated end-to-end goal; verified active through goal tool.
- You.com Web Search API accepted the provided credential and returned 3 official-domain source leads. Secret stays in ignored owner-only .env.
- Added tools/you_search.py; 3 software tests passed for credential placement/redaction, blocked redirects and malformed-result handling. These are software tests only.
- Recorded current interpreter/platform inventory. No simulator/training libraries in this interpreter; no physical K1 or configured Crusoe VM.
- Read Claude's 18:54:50 update; leave its migration/work-in-progress files untouched.

## 2026-10-17T18:57:28+00:00 — first remote checkpoint

- Commit `3d30864` pushed successfully to origin/main.
- Staged content passed credential, size, relative-link and whitespace checks.
- Claude code remains unstaged, preserving independent work until its ready handoff.

## 2026-10-17T19:21:02+00:00 — successor Codex audit and real-policy diagnostics

- Recovered the Codex role from current GOAL/ownership/status/handoff and live process state; preserved shared main and all Claude-owned files. Previous Codex result was stopped, with completed trial artifacts; no duplicate live job restarted.
- Verified official Booster source revisions and clean vendor worktrees; checked all original artifact hashes. Reproduced the 15 s / 0.2 m/s run exactly (same 750-row trajectory): 0.2802458334 m net world-X, 3.795028 degree peak base tilt.
- Added reproducible CPU and sim dependency instructions, real-policy checks, and artifact/trajectory auditor. Tests: 26 synthetic autonomy (46.23 s), 3 real-policy/model, 5 evidence-integrity, 3 search-client tests passed. Initial shell pytest commands failed because pytest was absent; isolated .venv fixed this without changing sim dependencies.
- Real-policy tests show exact actor output invariance to changing root world position and root linear velocity, correct command observation mapping, and finite physics stepping. Ideal simulator orientation/joints remain a hardware-parity limitation.
- Recorded all three additional frozen development commands (0, .35, .5 m/s), each 15 s rendered. Net world-X displacements: -.0073723, 2.595984, 4.575844 m. Stop-phase RMS world-XY speed: approximately 0, .0767, .1157 m/s. These do not establish stable arrival or load carrying. No project training or paid GPU resource used.
- Reviewed Claude's frozen handoff; reproduced degraded-localization false delivery, stale-pose acceptance and zero-speed follower movement. Exact findings and Q1–Q5 integration decisions recorded in CODEX_HANDOFF.md; diagnostic/noisy ground truth stays privileged. Checkpoint is a software scaffold with explicitly unresolved defects, not deployment approval.
- Video/trajectory artifacts remain local and ignored; their hashes and storage references are in experiment manifests/reports. No remote artifact storage configured.

## 2026-10-17T19:30:20+00:00 — review fixes validated and Brev provisioned

- Claude applied requested fixes and a further direction-change speed-bound regression. Rechecked all 37 frozen file hashes. Exact frozen suite: 34 passed, 1 skipped in 47.33 s; skipped camera module independently checked against sim MuJoCo in six poses plus neutral optical convention.
- A broad suite run temporarily observed an unfrozen depth-layer test failure (35 pass/1 fail/1 skip); recorded it to Claude. Claude fixed hit-cell dilation and reports 4 depth tests passing, but those new paths remain excluded from this checkpoint pending independent review.
- Brev login succeeded via checksum-verified CLI v0.6.337. Organization matched, initial instance inventory empty. User approved $1.74/hour Crusoe L40S; created `k1-isaac-check-20261017` (opqm34emo). Live state DEPLOYING.
- User extended authorization to next 5–6 hours including 17:15–18:30 PDT demo. Cancelled old two-hour guard (session33528 exit130); no automatic shutdown armed. Keep this instance for demo and only stop early if clearly unused. No duplicate instance/fallback authorized.
- Budget guard helper has three software tests; six total integration tests pass (guard + You.com client). Guard is a local cost-control tool, not an agent heartbeat.

## 2026-10-17T19:56:53.822961+00:00 — GPU runtime and realistic café progress

- User retained one L40S through17:15–18:30PDT; no automatic shutdown armed. Driver565.57.01→580.178.04 upgrade passed after targeted obsolete-library repair and OS reboot. Original failure retained.
- Installed Python3.11.13, IsaacSim5.1.0, IsaacLab2.3.2 tag (package0.54.2), Torch2.7+cu128. CUDA tensor test passed. Fixed flatdict legacy pkg_resources build dependency with setuptools80.9.0; reconciled package versions. One upstream metadata conflict remains: Lab pins Starlette0.49.1 vs Sim FastAPI0.115.7 requires<0.46. No web API service used; runtime behavior must be verified independently.
- Added explicitly privileged MuJoCo head RGB-D adapter.14 real model/policy/render/FK tests passed. macOS depth backend warns about unavailable ARB_clip_control; two2m plane samples satisfy1cm check only.
- User prioritized realistic scene and hackathon presentation. Sourced Poly Haven CC0 furniture/materials/HDRI viaYou.com+officialAPI;24 files SHA256 locked. Fixed two missing USD roughness EXRs in vendor package metadata. Native scene builds1251USDprims:6tables,18chairs,3plants, texturedfloor, windows, pendant/daylight, servicecounter and physicalbox/drink staged on tray.3USD dependency/scale/collision tests passed. Assets remain ignored.
- First actual Isaac smoke/café render failed with empty camera buffers and missinglibGLU errors. Installedlibglu1-mesa; retry02 launched. Nativeapp.close returnedexit0 despite Python failures; pipeline now asserts manifest status before accepting success. No scene screenshot or simulator success claimed yet.
- Reviewed new Claude handoffs and identified two provenance blockers: fixtureGT+bias mislabeledESTIMATED under a fully-deployable claim; BoxLifter/TabletopDetector fail to propagate privileged pose/extrinsics. Requested fixes/refreeze; no new Claude paths staged.

## 2026-10-17T20:14:29.666771+00:00

Café04 rendered four1280x720 PNGs on L40S; all hashes verified after download. Visually reviewed hero and counter: textures correct, enclosed interior legible. Preserved earlier negative attempts. Runtime audit and successful physics/RGB smoke saved. Received Claude complete78-file freeze20:12:47Z; review pending.

2026-10-17T20:15:28.285268+00:00: Final café USD checks3passed; camera/model suite14passed. Initial rerun used nonexistent test_upstream_k1.py and collected nothing; corrected to test_k1_policy.py. Claude78hashes match; video timing review found2.5Hz capture encoded10fps and unrecorded2s finalhold; requested honest captions before integrating experiment report.

2026-10-17T20:16:34.458331+00:00: Pushed d034f09 owned scene/runtime checkpoint. Verified exact frozen autonomy set54passed16skipped and31realcamera tests. Core review complete; committing19corepaths only. Presentation review found acceleratedclips and staleablationgenerator; sent targeted corrections, leaving those artifacts uncommitted.

2026-10-17T20:23:10.277781+00:00: RGB-D01verified12artifacts,5geometricchecks passed. Initial patchcheck counter failed because upperrayshitcounterface; corrected analytic nearest floor/counter intersection, same1cm tolerance. Import01failedmissingcameraextension;02activeafterexplicitactivation. Presentation66filescommitted6600726 with hashes/timing independentlyverified. User asked completionandtraining: estimated~30%fullgoal, explicitly noPPO/VLAupdates yet.

2026-10-17T20:28:16.726115+00:00: Import03verified22joints/camera, nominalPDfell1.472speak60.23deg. Completedprocesshunginshutdown; recordedSIGTERM, processnowabsent. SDKclose(wait_for_replicator=False) verifiedandappliedfuturejobs. Realunchangedactorwalk01nowlaunched with explicitPD+MJCFarmature. IndependentCL-5read-onlydetectorrerunmatchedall6capturecount/counteroutputsandprivilegedprovenance.

## 2026-10-17T20:40:55.982580+00:00 — corrected Isaac walking verified

Walk04:19.666kg,15s,750 actor calls,2.91964m,4.36846deg peak tilt, no fall. Ten evidence hashes and two375-frame/15s videos verified; head camera view visually corrected. No PPO/VLA update. CL5 eleven frozen hashes verified; independent offline detector rerun agreed with3/4targets and documented counter mislabel. Next: supported tray and loaded baseline.

## 2026-10-17T20:58:06.750094+00:00 — actual carrying PPO and negative evaluation

Added explicit0.95kg torsofixture and1.3kgfreepayload; loadedbaseline droppeddrink6.442s/1.2463m whilebodyupright. Pilot8env1024transitions/eightupdates verifiedactor+criticchanges. PPO02trained32env/100iterations,204800transitions/1600updates in293.295s;663episodes (449drops,214timeouts,0falls). Baseactorhashunchanged. FinalresidualCPUexport exacton32testinputs. Firstmatchedcaféfinal-checkpoint evaluation stillFAILEDdrinkdrop12.126s/3.22968m,bodytilt4.003deg. Singledevelopmentcomparison,notrepeatedorheld-outimprovement. Rawvideos+weights preservedoutsideGit.

Newtests:2payloadgeometry/mass,1batched-upstreamactorhistory/reset equivalence,2PPOGAE/update,1CPUexport equivalence allpassed. READMErewrittenwithrealpictures,currentresults/failures,andarchitectureusingCL6proposalasinput. Claude localizationfreeze remainsunintegratedpendingidentitymerge/goalshortcutreview.

## 2026-10-17T21:30:20.122442+00:00 — carrying fixture transfer checkpoint

Wider evaluator repeat preserved original baseline/PPO drink drops at6.442s/12.126s. New four-wall cup holder adds0.08kg; unchanged baseline completes15s without drop but fails4cm movement threshold at8.419cm. Unchanged trainedPPO02 on identical holder passes:15s,3.55766m,3.311cm movement,4.220deg bodytilt,.01756m/s finalspeed. One scripted development trial, not camera-guided delivery or repeatability. Both archives verified14 artifact hashes,375frames/15s and750 trajectory samples;3payload tests pass. Actual final frame inspected. Reports preserve mechanical assistance and negative baselines. VLA training has not begun.

## 2026-10-17T21:49:29.430683+00:00 — sensor-derived navigation and retained failures

Added nativegyro/joint telemetry, strict500Hz relativeheading integration, provisionallegheight and sensor-derived cameraextrinsics. Real20sturn gyroerror droppedfrom2.35rad at50Hz to.03044rad at500Hz; same-trajectorycomparison verifiesaliasing. Legtranslation stillfailed~2.05mdrift, excludedfromnavigation. RealMuJoCocamera-to-walking withsingleunnumberedtable, operatorfloorplan/initialposeprior andestimatedpose achievedmax9.74cmXYerror butstoppedambiguousdestination duefalsewallcornertable; capturedRGBDandhandedregressiontoClaude. Onefailureexactlyreproduced. Historicalsource/archive/artifact hashes verified.7sensor tests pass; oldlocalizer/CL7freeze9pathsreviewed/hashed; broadtest excludingliveheadingWIP62pass16skip1xfail. Liveperception/heading editsnotincluded.

## 2026-10-17T22:09:19.732333+00:00 — Appearance, navigation and VLA prerequisites

Pushed a9d8f62 with actual dark/light K1 materials, failed appearance attempts, one19s sensor-estimated unloaded approach and GPU SmolVLA probe. Reviewed Claude tabletop freeze;8tests pass. New10trial varied collection yielded4delivered/6timeouts, onecontact; three train episodes262frames and one validation149frames. All1791artifact hashes verified; 3dataset tests pass. Smoltrain01 failed beforeupdates onbfloat16hash; fixedraw-bytehash and launched02samebudget. UserHFaccesscheckedHTTP200; isolatedGR00Tdependenciespass,downloadsactive.

## 2026-10-17T22:14:26.266092+00:00 — First real SmolVLA fine-tuning verified

Attempt02 completed200updates/20.264s onL40S;122parameter tensorschanged,L2delta7.3128,frozenbackbonehashunchanged.16rowofflinevalidationMSE0.5953→0.1690. Savedcheckpointsha ca7e0eb430bc5896ee0639a880a3cef05f4fb0a684bb72a7c4f57ecce1907f53 independentlychecked; strictreload reproducedhashes andfiniteactionsfromactualvalidationframe. GR00Tsetupcompletewithpinnedweights/import/dependencycheck, noinference/training. Goalstillactive; nofullorhardwaresuccess.

## 2026-10-17T22:32:40.588434+00:00 — payload realism, comparison, W&B
You.com official packaging research saved; original Domino’s-inspired box textures and official Coke wordmark applied to non-colliding USD render shells. Local stage construction and six control/payload checks pass. ActualrenderqueuedafterVLAcomparison. Comparison01 importfailure retained;02runningaftermissing pinnedassetpackageinitializerdeployed. PrivateW&B historicalexportcompleted,alloriginalmanifest/metricshashesmatchlocal,evidencein92ca2f2.

2026-10-17T22:55:52.388482+00:00: hand09 .4m/s commanded trial achieved2.036m net with freehandcontact support, no drop/fall; hand08 .25 didnotwalk. Preserve alldevelopmentattempts.

2026-10-17T23:08:37.245951+00:00: Isaac hand03 and camera-repeat04 passed15 s/2.193 m with8.038 mm payload shift, no drop/fall/other-robot support. All14 artifacts per run and four hand-specific source snapshots verified; decoded375 frames/25 fps/15 s for both cameras. Root and contact CSVs identical across camera repeat. Real lower-angle image confirms tray seats rest on hands. Failed01 uv path and02 invalid USD prim name retained. Preparing exact-path checkpoint; Claude café-film handoff ready.

- 2026-10-17T23:35:00.823112+00:00 Loaded05 integratedcamera-guidedhandcarry passed14individualchecks (earlier15countincorrect),621frames25fpsbothviews verified. GR00T02 completed500updates,validationworsened38.9%,strictreloadpassed; callbacklogs missed20trainingrows, honestgappedgraphproduced. Correctedlogger03 nowrunning realupdates. Sourcehashes verified and reports prepared.

- 2026-10-17T23:47:49.979805+00:00 Verified GR00T03 500/500 loss logs,21fixedvalidations,22.3%lower offline loss, strictreloadpass; prior02worseningretained. Variedloaded3/4; pureyawprobeisolates1.6–1.8munintendedtranslation. Printed02delivered65.6+2s,original60stimeoutretained;1691framefilmverified. GR00Tloadedmatchedbatch now running via localhost SSH inference on authorizedL40S.

## 2026-10-18T00:10:00.636881+00:00 — Interactive Isaac desktop verified

Userpriorityimplemented:actualIsaac5.1GUI+nativeStart/Pause/Reset onexistingL40S. noVNCbrowservalidated sceneandinput;900physicsteps,pausedstateandresetposesverified. RemoteSSH-onlydesktopretainedthroughdemo. Trainingbeforepriority:handPPO32768steps1024updates,baseline4/8vsresidual3/8 diagnosticregression,notpromoted.

## 2026-10-18T00:35:35.993279+00:00 — live GR00T controls restored; two short runs

GUI182287: two user-requested previews4.24s/4calls/82acceptedticks and4.16s/4calls/78acceptedticks. Both manually paused/reset; final robot step0, GR00T selected. Browser confirms visible panel and robot. Earlier9.284s fall retained. Four focused tests pass. Report/source/screenshot/trace JSON under experiments/codex-20261018T0035-isaac-groot-live/. No delivery claim. Live MI verifier commit3a2c89e acknowledged; no edits to Claude WIP.
