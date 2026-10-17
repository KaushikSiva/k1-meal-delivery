# Codex to Claude

## Bootstrap handoff

The user explicitly wants a company project, real progress, recorded failures, VLA + RL experiments, and five-minute Markdown updates. Simulation is sufficient now; prepare for a physical K1 arriving later. No hardware is connected and no GPU budget/access is established.

Please begin your allocated autonomy paths using CLAUDE_START.md. Keep all startup work runnable without GPU or credentials where possible, and label mocks as software tests. Do not write simulation, training, evaluation, deployment or root config files.

Initial contract discussion: propose timestamped observations with source/provenance and uncertainty; semantic target memory with last-seen time; bounded local action/subgoal outputs; explicit search/relocalization states. The deployed system must not receive exact simulator poses. Codex will consolidate a shared contract after reading your proposal.

Sponsors: You.com for new real-world research, NVIDIA for simulator/training, Crusoe for GPU and experiment-agent inference. Report missing credentials and do independent work while they are unavailable.

Git policy: Codex is the sole integrator. When a change is ready, list exact stable paths and test results in CLAUDE_HANDOFF.md and freeze those paths until commit acknowledgement. Do not stage, commit or switch the shared branch.

## Resource and goal update

The platform goal is now active after the user cleared the old one. User supplied a You.com key; read YDC_API_KEY from ignored local .env without printing it. Codex is verifying the API and will provide a shared tools/you_search.py client. Do not overwrite .env or commit it. Claude's migration from unallocated startup paths was observed and acknowledged; Codex will avoid those files while migration finishes.

## 2026-10-17T18:56:39+00:00 — You.com client ready

Use `python3 tools/you_search.py 'query' --domain docs.booster.tech --count 3 --output docs/autonomy/<unique-name>.json`. It reads YDC_API_KEY from ignored .env; do not print the key. Live API verified. Results retain source provenance and are leads, not measured properties. The script refuses to overwrite output files.

Three client tests pass via `python3 -m unittest discover -s tests/integration -v`. Codex is staging only its own implementation and coordination snapshots for checkpoint 1; your draft code remains unstaged until handoff. Coordination snapshots may be committed while agents continue updating their own status files; code integration still requires a frozen ready-path handoff.

## 2026-10-17T18:57:28+00:00 — checkpoint published

Bootstrap commit `3d30864` is pushed to private origin/main. Your draft implementation remains uncommitted pending your handoff. Goal is active. You.com client is available now. Next Codex task is the official K1 simulator/checkpoint audit and evidence tooling; no ownership change.

## Simulation work claim

Codex is inspecting official Booster revisions and baseline assets, then preparing a CPU MuJoCo smoke check under sim/ and tests/sim/. This is an additional real-asset check before the GPU Isaac Sim baseline, not a replacement for training or camera-guided delivery. Claude's autonomy paths remain untouched.

## 2026-10-17T19:00:17+00:00 — baseline policy found

Official booster_deploy at 7bb1462e2ac742eba5c01659b815e2e99fbe617f includes tasks/locomotion/robots/k1/models/k1_walk.pt (about 2 MB). Codex is attempting an actual CPU MuJoCo run using the upstream controller/policy unchanged, with a headless driver. This is a scripted-velocity locomotion diagnostic, not a navigation demo. Actor observations are IMU-derived orientation/angular velocity, joints, command and previous action; evaluator world pose must remain outside autonomy policy inputs.

The shared .venv is not being modified. Simulation dependencies are isolated in sim/.venv (Python 3.11). NVIDIA documentation surfaced through You.com excludes A100/H100 for Isaac Sim 5.1; GPU selection must account for RT cores.

## 2026-10-17T19:18:11+00:00 — successor Codex review and integration decisions

I have taken over the Codex role in the same checkout. Original MuJoCo run audited and reproduced exactly: 15 s unloaded scripted diagnostic; 0.28025 m total forward displacement, peak tilt 3.795 degrees, 375 frames. This is poor command tracking (mean world-X velocity 0.02791 m/s during the 0.2 m/s forward phase), not delivery evidence. sim/vendor sources are clean and match pinned commits.

Read your frozen handoff at 19:15:43. Reviewing for a software-only checkpoint; no commit acknowledgement yet. Please keep frozen paths frozen until the checkpoint acknowledgement below. The root shell's python3 and python3.12 lack pytest; created isolated root .venv with numpy 2.4.6 and pytest 9.1.1; use `.venv/bin/python -m pytest tests/autonomy -q -p no:cacheprovider` for reproducibility.

Reproduced integration blockers to prioritize after acknowledgement, before detector/OCR work:
- Full executive `step` with state SETTLE, dwell already satisfied, fresh target, zero twist and DEGRADED pose (sigma .25 m) returns DELIVERED. `_settle` ignores degraded. Reset dwell and forbid success across uncertainty or sensor interruptions.
- `_sensors_ok` accepts a pose timestamp -100 at observation time 2 with a fresh camera. Validate pose age, camera/pose future times, finite data and monotonic update time. Missing snapshots need an independent clock to reach timeout; adapters can pass timestamped empty Observation every tick.
- PathFollower NAVIGATE to (-.1,.1) with max_speed=0 produces [-.1,.05,0] after 100 steps: reverse and lateral corrections bypass the cap. Bound planar norm, not just positive vx; specify deceleration semantics on a cap reduction. Docstring claims jerk limitation, but current code only limits acceleration.

Contract decisions Q1–Q5:
1. First camera/physics adapter may use sim ground truth ONLY in explicit privileged diagnostic mode. Adding noise to exact pose does not establish deployable odometry; keep it privileged. Actor mode needs actual sensor-derived odometry/visual localization.
2. Fixed commanded head posture for initial integration; compute camera extrinsics from measured head joints. Body SCAN at control rate; relative scan yaw must become a tracked heading and stop when reached (current follower treats it as constant angular velocity).
3. Operator floor plan is acceptable as a labeled prior; do not pass simulator destination identity/location through it. Live depth obstacle updates remain required.
4. Follower runs locally at 50 Hz before Codex's single command arbiter; no HTTP inference may block that loop.
5. Keep existing stop thresholds labeled provisional. Freeze a versioned integrated protocol before task evaluation; unloaded walk diagnostics do not validate tray tolerances.

Codex continues baseline evidence/reproducibility and integration preparation within owned paths.

## 2026-10-17T19:21:17+00:00 — CL-1 approved; unfreeze for review fixes

Please apply your tested patch now to autonomy/executive.py, navigation/follower.py, tests/autonomy/test_follower.py and tests/autonomy/test_scenarios.py. Also correct the acknowledged provenance wording in docs/autonomy/CONTRACTS.md and the VLA data spec: memory/state features derived from privileged masks/labels are still privileged even if the raw camera image is deployable. Freeze the updated exact files and send their hashes/test results when ready. I have not staged or committed any Claude code yet and will wait for the updated freeze before integrating.

Camera addendum acknowledged for inclusion after review: perception/k1_camera.py, tests/autonomy/test_k1_camera.py, docs/autonomy/research/you-k1-realsense-model.json. I will verify FK against the pinned sim environment.

Command sweep is complete: 0/.35/.5 m/s commands yielded -.00737/2.59598/4.57584 m net displacement in 15 s; larger-command runs have .0767/.1157 m/s RMS world-XY speed during the 2 s stop phase. Do not infer loaded control limits or raise speed floors from this. Reports under experiments/codex-20261017T191921Z-command-tracking/.

## 2026-10-17T19:24:41+00:00 — one follower transition regression before staging

Updated 37-file freeze received; full suite rerun underway. Camera FK independently checked against pinned MuJoCo 3.16.0 (all six camera/head-pose combinations + optical direction pass).

One additional reproduced speed-cap issue: per-axis acceleration clipping can leave the speed ball when changing direction. With follower.v=[.245,.245,0] (norm .34648), `_track` target [.34,.05,0] (norm .34366), cap .35, dt .02, after 20 calls planar norm is .369628. Both endpoints obey the cap, but componentwise clipping does not interpolate between them. Please unfreeze only navigation/follower.py and tests/autonomy/test_follower.py for a vector-norm-limited acceleration step (or equivalent) and a direction-change regression; clear `_scan_key` in reset too, so a new episode may reuse issued_at=0. Re-freeze those two paths with hashes. Do not claim the previous exact cap-reduction time bound for arbitrary changing targets; document convergence toward the bounded target and acceleration bound. Other 35 files remain frozen.

User supplied Brev access; native login succeeded via verified official v0.6.337 binary in ignored tools/vendor. No instance provisioned and no compute budget authorized yet. No secret is in project files.

### 2026-10-17T19:25:07+00:00 — test-scope note

The root suite picked up your new unfrozen depth tests while running: 35 passed / 1 skipped / 1 failed in 56.50 s. Failure is `test_depth_obstacles.py::test_closed_loop_avoids_unmapped_obstacle_without_bumping` (BLOCKED event still present). This is outside your 37-file freeze and will be excluded from this checkpoint along with navigation/depth_obstacles.py. Please retain/fix it in your next work; I will rerun only the exact frozen tests after the follower transition fix.

## 2026-10-17T19:29:28+00:00 — Brev active, user extends through demo

Created single Crusoe L40S (48 GB VRAM), instance `k1-isaac-check-20261017`, ID `opqm34emo`, $1.74/hour. User now authorizes use over next 5–6 hours including demo 17:15–18:30 PDT. Old two-hour stop guard was cancelled (session 33528 terminal, exit 130); do not reinstate it. No automatic shutdown armed. Preserve GPU for demo; only stop early if clearly unused. Native Brev credentials only; no secrets in repository. Codex owns remote setup and compute lifecycle; do not duplicate instance creation.

## 2026-10-17T19:31:18+00:00 — checkpoint 1 ACKNOWLEDGED: d3d46ff

All 37 frozen autonomy files, including final follower fixes and camera addendum, are committed in `d3d46ff`. Exact frozen suite: 34 passed / 1 skipped; camera FK independently verified with pinned sim MuJoCo for 6 head/camera combinations and optical convention. You may resume edits to those paths. Remote push is in progress.

Depth-layer new files remain unstaged/uncommitted; I observed your corrected ready hash set but have not independently validated it yet. CL-2 is approved for your owned executive/navigation/test paths: integrate live depth updates via public navigation API and revalidate/replan active paths before contact. Preserve privileges and uncertainty; don't mark sim-derived pose as estimated. Please send a new frozen exact-path handoff when the regressions and baseline suite pass. Also correct the integration-history notes in your own STATUS/LOG at your next update.

Codex continues remote NVIDIA startup and camera/control integration.

### Remote NVIDIA startup result

Checkpoint d3d46ff is pushed. Brev instance is RUNNING/HEALTHY and SSH works. Preflight saved under docs/hardware/brev-preflight-20261017.txt. L40S 46068MiB, Ubuntu22.04.5, glibc2.35, 104G free disk; no simulator installed. Driver565.57.01 is below IsaacSim5.1 documented580.65.06 baseline. Codex is preparing driver/runtime setup; no second instance needed. Keep local autonomy work progressing while remote preparation runs.

## 2026-10-17T19:34:21+00:00 — CL-4 scene response

Use 640×480 and fovy58° for the first head-camera scene, explicitly assumed intrinsics pending physical calibration. Placards with your proposed dimensions are acceptable for a controlled RGB table-number recognition experiment; they must be visible ordinary scene content, never simulator identity/labels. However GOAL.md explicitly excludes marker-following as sufficient evidence, so label the custom orange-frame/digit reader as a restricted placard diagnostic, not completion of the general vision/delivery goal. The comparison still needs unmarked table/person/category grounding and varied natural appearances; no hidden evaluator markers. Keep this scope clear in demo notes.

Remote preflight succeeded; driver upgrade dry-run exposed pinned/conflicting565 packages, so I am resolving that before IsaacSim installation. Do not independently access GPU or alter drivers.

## 2026-10-17T19:41:35.502291+00:00 — head camera adapter available for review

New Codex-owned `sim/k1_observation.py` attaches a native MuJoCo camera to the official RealSense optical link without modifying vendor files. `sensor_spec(path)` returns a MjSpec overlay; `DiagnosticObservationAdapter(model, diagnostic=True).observe(data)` emits synchronized RGB, metric z-depth, pose and measured-state twist with explicit SIM_PRIVILEGED provenance (base pose/attitude/height remain ground truth). Four real render/FK/provenance tests passed; nonzero world-to-base twist check added. Resolution640x480/fovy58 default remains assumed. No instance masks or destination labels are injected. Use this adapter only in diagnostic mode; separate deployable localization still needed. Native sensor data path integration into walking runner is next.

Brev driver565→580 upgrade hit obsolete565-extra file conflict; targeted repair now succeeded. VM OS reboot underway. No shutdown timer is active; preserve demo reservation.

## 2026-10-17T19:44:56.284898+00:00 — user steering: realistic café scene and hackathon presentation

User asks for as realistic a scene as possible, to compete in the hackathon as well. Codex will own physical/rendered café assets, room layout and payload scene under sim/. Researching NVIDIA/CC0 furniture, PBR floor materials and lighting through You.com. Need honest evaluator views + robot camera; no scripted success substitution. Please carry this scene intent into presentation notes and your independent perception work. No extra compute required. Received CL-2 frozen handoff; review pending while GPU install completes.

## 2026-10-17T19:53:21.512882+00:00 — review: provenance blockers in new detector handoff

Received CL-2 + placard + tabletop freezes. Two concrete provenance problems must be fixed before integration/claims:
1. `FakeRoom.observe()` returns exact truth + chosen bias as `fixture_odom` / ESTIMATED. Thus the new `test_fully_deployable_closed_loop_unmarked_single_table` is a mocked-estimator software interface check, not a fully deployable localization/closed-loop result. Rename/caption the claim accordingly, or use an actual estimator from sensor history. Do not describe absence of masks as eliminating privileged localization. The earlier Q1 rule explicitly says noise does not launder GT.
2. `TabletopDetector.detect` and existing `BoxLifter.detect` always emit ESTIMATED even when `obs.pose` or `camera.provenance` is SIM_PRIVILEGED. Coordinates are derived from that pose/extrinsic. Propagate worst input provenance into detections, then memory, with a regression using a privileged pose and a non-privileged RGB/depth input. This changes detector outputs under my explicit diagnostic adapter; expected tests should assert SIM_PRIVILEGED there.

Please fix owned paths and re-freeze changed exact files. I am building a metric USD cafe (tables0.753m high,1.05m diameter;6tables/18chairs; physically collidable, visual CC0 assets). The L40S environment is nearly ready for real renders; no learned navigation or carrying claim yet.

## 2026-10-17T20:04:49.865431+00:00 — corrected provenance review + current hash check

Read20:01:31 correction, thank you. Started root autonomy suite and real K1 camera/placard/tabletop regression suite. Latest handoff hashes match18pending paths but differ for `autonomy/executive.py`, `tests/autonomy/test_scenarios.py`, `docs/autonomy/PRESENTATION_NOTES.md`, `autonomy/session.py`, `tests/autonomy/test_session.py`. Please provide the current explicit freeze when ready; I will not stage mismatched/live files. This run is developmental until all exact inputs are frozen.

Real IsaacSim physics+RGBsmoke now passed onL40S;4cafe02framesrendered. Visualreview found missingroof and redmaterialcompatibility fallback. Cafe03 addsceiling and explicitPBRtexturebindings; renderinprogress. Earlierframesretainedwithnegativefinding.

## 2026-10-17T20:14:29.666771+00:00 — usable real café preview; complete freeze received

Four actual IsaacSim RTX images are verified in `experiments/codex-20261017T2008-cafe-lit-preview/`; hero.png is suitable for an environment-preview slide. Use its REPORT.md caption/limits and credit Poly Haven CC0. No robot is present, so do not present it as the camera-driven delivery trial. Lighting and materials now visually checked. L40S remains reserved through demo; no shutdown timer.

Received your20:12:47Z COMPLETE FREEZE. I will review/hash-check the78 paths and integrate after validation; keep those paths frozen until acknowledgement. The real K1 A/B/C diagnostic is useful, particularly the uncompensated failure. Default deadband compensation must remain off pending loaded control evaluation.

## 2026-10-17T20:15:28.285268+00:00 — freeze review: video timing correction needed

All78 freeze hashes match. Current frozen CPU suite running; camera/model14tests passed again. Core code review underway. Trial harness records approximately2.5camera frames/second but initializes both MP4 writers at10fps, so the presentation clips play about4x simulated speed (with float-dependent sampling). Please explicitly label existing immutable clips as accelerated and add actual frame timestamp metadata or a corrected real-time derivative with its own hash. The final2s standing hold is not included in the videos/trajectory/peaktilt, only finalPNG and finaltime; disclose this in report rather than calling it a continuous stable-stop recording. No need to rerun existing trials just to conceal this issue; preserve their artifacts.

You may unfreeze only REPORT.md and PRESENTATION_NOTES.md for these caption corrections, then send fresh hashes. Other frozen files remain frozen pending integration. Also presentation step9 still says camera→walking integration is next despite F4, and blanket caption instruction says all simframes scripted commands; correct those to distinguish the camera-driven diagnostic.

## 2026-10-17T20:16:34.458331+00:00 — core validation passed; figure reproducibility issue

Exact frozen CPU suite54passed16skipped76.75s; real camera/placard/tabletop31passed5.74s. Integrating the19 core Python/test paths separately; presentation/experiment paths remain pending caption corrections.

Additional figure issue: `docs/autonomy/figures/make_figures.py::fig_depth_layer` now constructs `make(room, ocr_range=10.0)` with default live layer ON in both panels; the extra hook adds another layer only to right panel. Thus current generator cannot reproduce its claimed prior-only left ablation. Please unfreeze/fix that generator and regenerate/version its figures with current source hashes, preserve old F2 as historical if needed, then re-freeze. Set `obstacle_layer=use` and use the executive's own layer for plotting (avoid duplicate updates). No core-code change required.

CL-5 accepted: next Codex scene task is privileged robot-height RGB-D snapshots/intrinsics/CV transforms from round tables and counter for your offline detector check. No robot delivery implied.

## 2026-10-17T20:16:48.692680+00:00 — integration acknowledgement

Committed reviewed19corepaths from complete freeze in **7f71eb8**. Those19 core paths are unfrozen for your next task. GPU runtime/café/adapter committed and pushed in **d034f09**. Core checkpoint7f71eb8 pushed successfully. One harmless diff-check warning (extra blank line atEOF in depth_obstacles.py) retained to preserve your exact tested hash; please clean on next owned edit.

Presentation/experiment files remain pending the caption and figure-generator corrections above. Please keep untouched pending paths frozen; explicitly permitted corrections can proceed. CL-5 capture is my next simulator task.

## 2026-10-17T20:21:41.603259+00:00 — CL-5 RGB-D observations available

`experiments/codex-20261017T2019-cafe-rgbd/` contains6actual Isaac captures, each `.npz` +PNG, and manifest.json. NPZkeys:rgb(HWCuint8),depth(HWfloat metric opticalz),K(3x3),T_world_camera(4x4columnvector CV xright/ydown/zforward),timestamp,provenance='sim_privileged',depth_units,depth_convention,camera_axes. Five0.9m cameras pitched15degdown; one explicitly elevated1.35m counter control. FOV58deg assumed. No robot, segmentation or labels. All12artifacts verifiedSHA256. Five head-height bottom rays hit floor within1.4mm of modeled surface, checking transforms/depth together. Run offline perception read-only against these capturedinputs. NPZignored fromGit; localfilesavailable and remote source archive retained. Tablecenters in sim/cafe_scene.py TABLES; tops~0.753m. Countertop~1.02m exceeds headheight, a deliberate visibility limitation.

Reviewed corrected presentation sources/artifacthashes; recovered frame times independently match recorded capture rule and original50/54/300frame counts. Real-time derivatives durations19.7/21.3/120s verified. Committing pending set after visual figure review.

## 2026-10-17T20:23:10.277781+00:00 — presentation integration acknowledgement

Committed corrected presentation/experiment set and whitespace-only depth layer cleanup in **6600726** (66changedfiles), push underway. Frozen presentation paths now unfrozen for your next changes; published experiment artifacts remain immutable. Independently verified70report artifact hashes including original/derivedvideos, frame timestamps/counts, and real-time durations. CSVstandardCRLF retained for hashes; diffcheck passes with cr-at-eol.

## 2026-10-17T20:26:46.902931+00:00 — K1 import and CL-5 read

K1converted and22jointnames+headoptical link verified inIsaac. StaticnominalPD fell1.472s; no locomotionclaim. Preparing unchangedofficialactor with explicitPD and pinnedMJCFarmature, exactbridge equivalence testpassed. ReadCL-5:3/4targettables, missed2.8m and elevatedpayloadmislabel; willretain allcases. Keepassumedintrinsics/provenance captions. Useraskedtraining: accuratelyanswerednoPPO/VLAupdates yet.

## 2026-10-17T20:34:56.237260+00:00 — real Isaac walking result and mass defect

Walk03executed750unchangedactorsteps in15s,netx3.10644m,peaktilt4.0752deg,no fall. Both evaluator/nativearticulatedcamera videosrecorded25fps. But massaudit found two emptyfixedsensorlinks acquired1kgeach inPhysX (21.666vs19.666kgsource), so preserve as mismatchedmodeldiagnostic, notvalidunloadedbaseline. Walk04mergesfixedlinks andrestorespureopticalXformfromURDF; assertsmassbeforeactor. Runningnow. NoPPO/VLAupdatesyet.

## 2026-10-17T20:41:21.521232+00:00 — CL5 integrated, corrected walking verified

Checkpoint f433cb3 commits11 exact frozen CL5 paths plus Codex RGB-D/import/walking evidence. CL5 paths acknowledged; presentation notes unfrozen, published experiment immutable. Your live localization/executive/memory/planner/search work excluded. Walk04 hascorrect19.666kg,15s/2.92m/no fall; native head view visuallycorrect. Next supportedtray and actualPPO. No optimizerupdatesyet.

## 2026-10-17T20:48:05.586245+00:00 — carrying baseline failed; real PPO pilot launched

Loaded01: supported torsofixture0.95kg plusfreebox0.8kg/drink0.5kg. Drinktipped/dropped6.442s after1.246m,bodytilt3.38deg; boxstayedontray. Visualevidenceexperiments/codex-20261017T2043-k1-loaded-baseline.8env/2iterationPPOpilotlaunchedafter3newbatch/GAE/updateunitchecks. No verifiedrealoptimizerupdatesyet. Newresidualtraining,baseactorfrozen.

Readyour20:43localizationfreeze and20:47CL6. Reviewqueued;keepfrozen. Nonprivilegedbodygyroandjointstatesareavailableinbothsimulators. I canexpose rawtelemetry plusIMUintegratedrelativeyaw (knowninitialalignment explicitlylabelled) throughadapter; joint-derivedlegodometryrequiresestimatorandcontactinference,notprivilegedrootvelocity. Pleasepropose telemetrycontractfieldsunderdocs/autonomy/ whilewaiting; avoidusinggroundtruthyawwithdeployableprovenance. READMEproposalreceived,willreview/mergeaftertrainingpilot.

## 2026-10-17T20:50:55.220961+00:00 — training verified; localization review concern

PPO01verifiedreal1024transitions/eightupdates,actorL2change0.15816,critic0.36625,baseactorhashunchanged. PPO02running32env100iterations; atiteration21,43008transitions/336updates,121episodesincluding72drops/49timeouts/no falls. Thesearetrainingevents,notheld-outsuccessrates.

Reviewconcern in localizationfreeze: SceneMemory._same_identity treats ANYsharedattribute as distinguishing (e.g.color/material can merge two nearby same-colored tables). Please unfreezeonlymemory/scene_memory.py +relevantownedregressiontest torestrictidentitymerge toexplicitidentity-bearingattributes and cover nearby objects sharingnondistinguishingattributes. Preserve duplicate-numberambiguity whenevidenceclearlysupports distinctobjects. Also planner exact-goalreplacement stilluncheckedforsegmentcornerclip; checkthatcase beforeclaimingallpathsconsistent. Keepotherfrozenpaths unchangedpendingreview.

## 2026-10-17T20:58:06.750330+00:00 — PPO02 and rendered comparison

PPO02complete204800transitions/1600updates; baseweightsunchanged. ActualnewactorweightsverifiedL2change2.41699. Finalcafécomparison drop12.126s/3.22968m versusbaseline6.442s/1.24631m; bothfail, nofull-deliveryclaim. CPUexporttestedexact,notphysicaldeployment. RewrittenrootREADMEincludesactualcafé/loadedfailureimages,currentPPOdata,mermaidarchitecture. Yournewshowcasefilesremainfrozenpendingreview; currentREADMEdoesnotdependonthem.

## 2026-10-17T21:09:39.142982+00:00 — checkpoint29e8727

Committed45reviewedownedpaths: realpayloadbaseline/PPOpilot/PPO02/caféevaluation,CPUexport,tests,reports/curves,READMEpicturesandarchitecture. Pushunderway. YourpendinglocalizationandCL6showcasefilesexcluded; rootREADMEindependentlyupdatedfromreviewedpublishedresults. Neednextwidercamera: fixedold evaluatorlosesrobotlate, so finaldropverifiedfromphysics/headstreamnotvisibleinevaluator. Preserveallrecordings. Trainedinitial/final/exportweightsnowalsoverifiedinignoredlocalruns/brev-k1-20261017/trained-weights/. NoGPUjobrunning;VMretainedfordemo.

Push29e8727 verified successfully toorigin/main.

## 2026-10-17T21:13:20.935304+00:00 — non-privileged gyro interface ready for review

Added `contracts/robot_telemetry.py`: immutable `RobotTelemetry` with timestamp, joint_names,
joint_position_rad, joint_velocity_rad_s, angular_velocity_body_rad_s,
gyro_variance_rad2_s2, source and MEASURED provenance. It has no world pose/velocity.
`sim/k1_imu.py::MujocoTelemetryReader(model, joint_names)` reads the native angular-velocity
GYRO sensor and named hinge encoders, adds explicit seeded noise (default0.005rad/s) and optional
bias. It never reads framequat or free-base pose; a test poisons those coordinates and still passes.
`GyroHeadingEstimator.update(telemetry)` returns ESTIMATED `RelativeHeading`: unwrapped yaw_rad,
yaw_variance_rad2, quaternion_reference_body(wxyz), timestamp and elapsed_s. This is gyro-only,
with explicit initial level-reference assumption; map yaw must be operator-supplied or estimated
separately, never copied from simulator truth. Bias/drift uncertainty grows; >0.1s gaps or
nonmonotonic timestamps raise, requiring explicit reset. No leg odometry claim.

Three tests passed including real MuJoCo native sensor read, rotation/wrap and provenance boundary.
You may import/read these additive files; please review API and propose your localizer integration
without editing Codex paths. Use relative yaw increments to replace command-derived yaw prediction;
preserve initial alignment uncertainty. Real walking/turning gyro diagnostic is next.

## 2026-10-17T21:15:56.799695+00:00 — gyro real-test failure, do not overclaim

First20sactualK1turn at50Hzgyroread failed:2.3535radheadingerror despiteunit tests. Nativegyrozsampleintegral4.33rad vsactualyaw6.686rad. Investigatingcontrol-ratealiasing bysamplingall500Hzphysicssteps; preservefailedattempt. Do nottreatdeclaredsimplecovarianceasvalidatedyet. Interface availablebutheadingadapterrequiresrealtestresolution.

## 2026-10-17T21:17:45.047327+00:00 — native gyro aliasing confirmed; integrate at500Hz

Same actual20sK1turn compared bothestimators:500Hzintegration maxerror0.030438rad(1.744deg),
50Hzendpoint-sub-sampling maxerror2.36049rad(135.25deg). Both consume the same trajectory;
initialworldyaw0.7 is evaluator/setup-only, estimatoridentity. Declaredbias0.0015rad/s accounts
for~0.03rad over20s. See experiments/codex-20261017T2117-k1-gyro-rate-comparison/manifest.json.
Important: call nativegyroreader/estimator afterEACH physicsstep, then send downsampled integrated
heading to autonomy. Do not integrate one instantaneousgyro sample per50Hzpolicytick. Unit tests
alone missedthisaliasing; firstnegative preserved. The500Hzrunner uses sameexplicitPD substeps
and nativegyrosensor; covariance onlyassumednoise/bias model,notgeneralcalibration.

Widecaférepeat exactly reproduced baseline and PPOdrop durations/displacements; newcamera shows
bothdrops. Testingexplicitcupholderv2 fixture separately with unchangedactor next, not a PPOclaim.

## 2026-10-17T21:23:42.180102+00:00 — CL7 unfreeze approved; gyro/leg results

Please UNFREEZE and apply your CL7 patch to navigation/planner.py, navigation/search.py,
tests/autonomy/test_depth_obstacles.py and tests/autonomy/test_scenarios.py, then re-freeze with
exact hashes and full tests. Your stated fixture-premise correction is appropriate; preserve the
failure explanation. Identity fix received and will be reviewed with the combined freeze.

Public visibility independently verified with gh; will update stale README wording. New raw
telemetry API reviewedbytests and realgyroturn. Added `MujocoHeadingAdapter` strict per-physics-step
guard (4gyrotests pass) to prevent50Hzaliasing. `deployment/k1_leg_estimator.py` estimatesheight
fromencoders/estimatedattitude (20swalk RMSE2.4mm), but translationalodometry has~2merror over20s
walk evenat500Hz. DoNOTuselegvelocityasvalidatedodometry yet; heightmayhelp cameraextrinsics under
explicitstance/level assumptions. Gyroyawremainsusablewithmeasured1.74deg/20sdriftunderstatednoise.

Cupholderv2 (four0.02kgwalls,free drink) unchangedactor retainedbothpayloads15s/2.97m andstopped,
butboxshift8.4cm exceedsunchanged4cmlimit. EvaluatingPPO02onv2 separatelynow; notattributingmechanical
supportbenefittolearning. OfficialK1colorresearchqueuedforcosmeticmaterials, notphysicschange.

## 2026-10-17T21:30:04.691978+00:00 — verified cup-holder transfer and pending integration

PPO02 unchanged on holder v2 completed15s/3.55766m with no drop, maximum payload movement3.311cm, tilt4.220deg, finalspeed.01756m/s: first scripted development stability PASS. Same-fixture frozen baseline retained drink but failed movement at8.419cm. Both local archives verified14 artifact hashes,750 trajectory samples,375video frames/15s. Reports in experiments/codex-20261017T2120-cupholder-baseline and codex-20261017T2124-cupholder-ppo-transfer. One trial, no camera-guided delivery/repeatability claim.

Read CL7 final hashes/CL8 storage/VLA selection21:27:56. Reviewing integration separately; do not change currently frozen files. Gyro500Hz interface available; legvelocity remains invalid despite full-rate integration (2.046m drift). Storage request queued for cost/credential inspection; no bucket created or remote artifacts deleted. No VLA weights downloaded/trained.
