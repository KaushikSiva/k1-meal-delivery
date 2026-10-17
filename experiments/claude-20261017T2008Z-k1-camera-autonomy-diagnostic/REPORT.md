# K1 camera-to-walking autonomy — MuJoCo PRIVILEGED DIAGNOSTIC (Claude)

**Evidence kind:** simulator diagnostic with **privileged** pose. NOT deployable delivery evidence, NOT a payload/tray result, NOT hardware. Run by Claude (agent-prefixed run dir per OWNERSHIP.md).

## Hypothesis

The autonomy stack can drive the **official, unmodified K1 walking policy** (`k1_walk.pt`) from the K1 head camera's rendered RGB-D through velocity commands, finding a numbered table and stopping stably, when given the simulator pose. (It isolates perception → memory → executive → follower → walking from the unsolved localization problem.)

## Setup (exact)

- Code commit base: `d3d46ff013056f85c700b570bee968f2c0d0d7b8` + uncommitted Claude working tree (hashes below). Runner: `k1_autonomy_trial.py` in this directory (sha256 `73e43b6827665d488a81302ab7aa68aa5c7359ce15f2bc48c96cf0a74a774610`), run with `sim/.venv/bin/python` (Python 3.11, MuJoCo 3.16.0, torch per Codex sim env).
- Walking policy: `sim/vendor/booster_deploy/.../k1_walk.pt` sha256 `2d860167ed827e8d44cd65abd4c27f474904352bcb98c0cfa97c078f63e2fea5`, booster_deploy @7bb1462e, upstream controller unchanged; Claude's subclass only rebuilds the MjModel with Codex's head-camera overlay + static scene geoms (asserted: nq/nu unchanged).
- Camera: Codex `sim/k1_observation.py` DiagnosticObservationAdapter (RealSense optical link, 640×480, fovy 58° **assumed**), 5 Hz. Control 50 Hz.
- Scene: flat floor; table 3 box 0.8×1.0 m top at 0.75 m centered (4.0, 0.0); distractor table 1 at (2.6, 2.2). Each with a 0.2 m table-number placard (restricted placard diagnostic) facing −x. No payload, no chairs, no people.
- Autonomy: `AutonomySession` (executive + PathFollower), instruction "deliver the pizza and drink to table 3", detector `CombinedDetector(TabletopDetector(), BoxLifter(PlacardReader()))`, live depth obstacle layer on, `deployable=False`.
- Privileged inputs: map pose / base attitude & height / base twist (sim ground truth via adapter); operator floor plan containing the two table footprints (prior; does not mark which is table 3).
- **Deadband compensation (trials A, B):** `FollowerLimits(min_walk_cmd=0.3)` and `ExecutiveConfig(final_speed=0.3, approach/search 0.35)`. Rationale: Codex's unloaded command sweep showed ~0.03 m/s achieved at 0.2 m/s commanded. This is a **diagnostic setting for the unloaded walking policy**, not a validated loaded/tray speed limit (Codex: do not infer loaded control limits from unloaded diagnostics).

## Results (all attempts; 3 trials, 1 seed each, deterministic)

| Trial | Start | Deadband comp. | Termination | Outcome | Sim time (s) | Dist. stop→table-3 edge (m) | Peak base tilt (°) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | (0,0) facing tables | 0.3 | autonomy_terminal | delivered | 21.6 | 0.74 | 4.8 |
| B | (0,0) facing AWAY (yaw π) | 0.3 | autonomy_terminal | delivered | 23.2 | 0.46 | 7.0 |
| C | (0,0) facing tables | 0.0 | max_time | None | 120.0 | 1.45 | 4.8 |

Delivered-condition (executive, provisional thresholds): pose error ≤ 0.2 m, yaw ≤ 0.35 rad, measured base speed ≤ 0.03 for 1.5 s, table 3 seen within 3 s.

**Trial A executive events:**
```
2.0 search: search -> approach
11.2 approach: approach -> final_approach
15.8 final_approach: final_approach -> settle
19.6 settle: settle -> done
19.6 done: delivered at table#1: pos_err=0.035 m yaw_err=0.005 rad speed=0.002
```
**Trial B executive events:**
```
6.2 search: search -> verify
7.0 verify: verify table#0: confirmed
7.0 verify: verify -> search
7.0 search: search -> approach
13.4 approach: approach -> final_approach
17.4 final_approach: final_approach -> settle
21.2 settle: settle -> done
21.2 done: delivered at table#0: pos_err=0.082 m yaw_err=0.006 rad speed=0.002
```
**Trial C executive events:**
```
2.0 search: search -> approach
11.2 approach: approach -> final_approach
```

## Interpretation

- A, B: the full camera → memory → executive → follower → official walking policy loop reached and stably stopped at the correct numbered table, including a search from facing away (B: turned, saw a table, VERIFY read "3", approached). 2/2 with compensation; this is **n=1 per condition** — no rate claim.
- C (negative result, kept): without deadband compensation the robot stalls ~1.45 m from the table in FINAL_APPROACH (commands ≤0.15 m/s produce ~no motion with this unloaded policy) and the trial times out at 120 s. The executive did **not** declare success (correct). This motivates either a carrying controller that tracks low speeds (PPO, Codex) or a validated compensation; the decision belongs to the control owner.
- Bugs found by this trial and fixed before the recorded runs (in Claude working tree, software-tested): (1) resuming APPROACH after SENSOR_WAIT refreshed the interrupt's HOLD forever; (2) the session called the executive between camera frames as if sensors were missing. First recorded attempt also failed at harness level (relative output path broke MuJoCo texture loading; no physics ran); fixed by resolving the path; those empty dirs were removed.

## Limitations

- Privileged pose/attitude/twist; deployable localization not exercised. Placards are a restricted diagnostic cue (GOAL.md: marker-following is not sufficient evidence). Plain box tables, flat floor, no payload/tray, no people, assumed camera intrinsics, one seed per condition, MuJoCo only (not Isaac). Compensation parameters are hand-chosen for the unloaded policy.

## Artifacts (sha256)

Videos (`*.mp4`) are git-ignored; keep locally / external storage with these hashes.
```
c1e1be93c14254b99275d704302c3c6c2228021c2f9e42ddc1ff22463d7fec02  contact_trial-B.png
73e43b6827665d488a81302ab7aa68aa5c7359ce15f2bc48c96cf0a74a774610  k1_autonomy_trial.py
cc09f83ce3baa7214a184b3494fddd4dde1630c5f365372678cec4c6fd61b56a  trial-A/evaluator.mp4
4b66c16b04f4665cad4593bb59fa19281d8e596f759cc80e01730086ae3232e3  trial-A/evaluator_final.png
6e2b35bfe65dcbdf996ea8cf78d2654bfa84d2b869da139519776c05400b11a6  trial-A/evaluator_t000.png
86c1d3b910af5605843638db2f0288cf6f39c08733581a8758c508c0abaaf65c  trial-A/evaluator_t010.png
96b58e71eacaadc6b44a01ec22f3c9f41ec8e91e5c6600e4976b59edf9bc2f6b  trial-A/placard_1.png
63da4bb6aa83dd652de8bdbc7337b257ba48e73064760ee6d99aa130938854ae  trial-A/placard_3.png
3b1e275d466b42e830365d3a59e3f70ff665917b399e437f2f8f7cd390143c50  trial-A/result.json
a32b64f17d1a46899fc466a6f7c58fe129c9e04c68c769b8c27b0b581f90dfe1  trial-A/robot_camera.mp4
1f5b290fef25d166d904bdbfe9ddf138396b0a369d8d66758a9570d6369a8a35  trial-A/robot_camera_final.png
31ee12e41a987e4f47f118fd701a26959e819a60d47095e07a32534ba4f8eb82  trial-A/robot_camera_t000.png
3eaf081c2dd2919360f5552f8dedfb16a0f5adf752ab28d31d2272a708617205  trial-A/robot_camera_t010.png
a18a5e6ae093cbf5cf9441228b9f9560b6ce6f1806e7e2fbe38b1212e7c74fc7  trial-A/states.txt
2d063c2fcbd58df87ffeb1bf300fc785e6ac233bf3f5b673f86d4f479e9d3fc9  trial-A/trajectory.csv
90d72e41ee42a859ab011dc0aefe2bbe33f543f9be555323b76a5e840130cb84  trial-B/evaluator.mp4
ba6dedced012a9d62b8b2f806564cf5fae729eddfa70f4623b206844fd423796  trial-B/evaluator_final.png
0e4f215c650aa6e86dfbefde157d818cfcb820e9d1f7a1d0b6e4e181168a889e  trial-B/evaluator_t000.png
9e9f542e28bd7d432baaab8a55fa551700d77fca8561d406ced9be25f6aa4bd7  trial-B/evaluator_t010.png
ae6010cef93c13d38717c75e977a3e562d04f0292d53ef3b38e45e5f70ac213e  trial-B/evaluator_t020.png
96b58e71eacaadc6b44a01ec22f3c9f41ec8e91e5c6600e4976b59edf9bc2f6b  trial-B/placard_1.png
63da4bb6aa83dd652de8bdbc7337b257ba48e73064760ee6d99aa130938854ae  trial-B/placard_3.png
7e6f607f51a81173610db496094f7a2fb4c39ec806816e9aa3b979f65b955d1d  trial-B/result.json
a364c49eebe91effbd4c752ac3504aefae010de77af8b810bf6833d87ebd4e8b  trial-B/robot_camera.mp4
9597e6aa054e3a4de615486c5a231317e1232abc278a8c803b392bb4fb77eb64  trial-B/robot_camera_final.png
2cabc53c024dc688524e019eef598f90f7cd4e3f9adb6eac5498848cde13465d  trial-B/robot_camera_t000.png
0aa59262386d490dee5b0d9f0acc5f095217c8e3fb18a12322d807695c68fa4b  trial-B/robot_camera_t010.png
ae6f1ac1a73279b8eab6dac12427fb62efa0695dbf4ed9ad6573668fc54a2885  trial-B/robot_camera_t020.png
82232c06fefcdbdef41e3c4f83dfff942744371480affe62fcded94062e08c91  trial-B/states.txt
a0a66ab038002b63324e36891f2b16410d889a78590eac7dd08476cdaf056d1d  trial-B/trajectory.csv
73740dbdb601c6d616479e056470d1a32bdc9abd2e5ed0de1d76f96fd436640e  trial-C/evaluator.mp4
6e2b35bfe65dcbdf996ea8cf78d2654bfa84d2b869da139519776c05400b11a6  trial-C/evaluator_t000.png
86c1d3b910af5605843638db2f0288cf6f39c08733581a8758c508c0abaaf65c  trial-C/evaluator_t010.png
b23d8131916e081fd6bb9152cc157fe7adbc06833748c2f428d5ae5b3ad88f0a  trial-C/evaluator_t020.png
767cb8aa9558107577a441dac512725bbe27574bc017337784946ed6b32195d4  trial-C/evaluator_t030.png
9e0e77666d6925827d69f794aa268b5965d5fca0d7b712726723960c82f084f0  trial-C/evaluator_t040.png
a47eb9076aa542cd97f6c8439af81ffda9cd5c0073c03083aad77d76d71657b9  trial-C/evaluator_t050.png
9904509a83bdbfdb509f645de7bf41680c9fb0370251d870eec053631b0d6cdd  trial-C/evaluator_t060.png
0d1b218fd11ddd07358a43cfb4899c3cdb2d18cf9b0c593916e9b6cae73a8b92  trial-C/evaluator_t070.png
99c506b90fa99e89de3d2eea13a84db384a284eff815da5a75c1ba6966e9f3c8  trial-C/evaluator_t080.png
b3c9c664d8a6a9d79ac513b20681938998a2c4e9adc03f733e2c2d38cb5a5ebb  trial-C/evaluator_t090.png
07f460fa381456251c6755b75f4b14d7b2c51e76b1cbbc0f646cff183b831d69  trial-C/evaluator_t100.png
ac0453c6e2b4108f5b879c14803ca23d4d5ef408b9f77edd3ced55c0b3fb283a  trial-C/evaluator_t110.png
96b58e71eacaadc6b44a01ec22f3c9f41ec8e91e5c6600e4976b59edf9bc2f6b  trial-C/placard_1.png
63da4bb6aa83dd652de8bdbc7337b257ba48e73064760ee6d99aa130938854ae  trial-C/placard_3.png
9be2c084f9802c660dde83b646d879a9234bf454a5ac800b2e708256945e0fd5  trial-C/result.json
7aea629788e32529b2a0beecd22bfda32beecaa65478baf75b6ee5cc0b836d48  trial-C/robot_camera.mp4
31ee12e41a987e4f47f118fd701a26959e819a60d47095e07a32534ba4f8eb82  trial-C/robot_camera_t000.png
3eaf081c2dd2919360f5552f8dedfb16a0f5adf752ab28d31d2272a708617205  trial-C/robot_camera_t010.png
ff6e4286f15ec6f8d456066f4e5645e1a82f7219d4b540dabf213ab473d020a3  trial-C/robot_camera_t020.png
fb16e8f13058d451cbc340cc5304ad5bc90a6c4fe78471dee6b4cdb659db3ba5  trial-C/robot_camera_t030.png
c938b9b11f8bf11e462d8baae8208d495a31e9fbead49bccc63565ec80bd1a02  trial-C/robot_camera_t040.png
95bc4b276bd87b2b6cea98fb900dd594022e5cbcb5d6b7796032b8fccd79e56d  trial-C/robot_camera_t050.png
5f6e733d2f3dcfa517a679b2eb466e863c794b124c60eb940045847f583a2d91  trial-C/robot_camera_t060.png
36cb6cabce65b2f26ea5d4427883808b2da7f1a8626a3df12434c9d0842e9dbb  trial-C/robot_camera_t070.png
50927a391c407003a44a6a806ab04c321b1fe2db9f14e760f803132d90ace783  trial-C/robot_camera_t080.png
b51da2a3336c153e6b2f41077905c425e0a92e792861f9138d7ce0ef3d7854fc  trial-C/robot_camera_t090.png
52200813ff93b9f3aafe3a59c3ff37330a1ff2becdd1bbcd86b85be3104ded19  trial-C/robot_camera_t100.png
c0803ba79f52ec7943ec204fac274a15c30d41b2c363d922293f476661228912  trial-C/robot_camera_t110.png
e086fd9648168b036431668a4b808207e146b32bec49dc200fc2a39ef98148fa  trial-C/states.txt
61340d1f6073c5d9dfd072d90a0cc301faaca1aee91bf7a13271c34212f19515  trial-C/trajectory.csv
```
## Code under test (sha256)
```
12b0e9299bb555f7d56dc715efbd17e785efe013cac48c909af203d84805bb37  autonomy/executive.py
a68dd346013a7940672703f588da4534d62be8e4ce2ae55bb6e1d550add0fef8  autonomy/session.py
4d0fdb9f6c501e55d6368abaab3c523eba0b3fc8e6956579bb7fa02873f9b113  autonomy/grounding.py
4c894d963510f0c4f61111f8c9aa0113233077fb3cf7901bd0df56dc1bae3e51  autonomy/contracts.py
bad08d4ca6b4c9d38a5bc6f25aa0c9c604681b45adc60fedd5148b37cc40a4ea  memory/scene_memory.py
b0de96990252b5e5517110375e0237c37312b28bf624a5b42e97bde7f2786324  navigation/follower.py
c37cc8e0b0bf664383cd823b23f53ee0cd979d4eddce3b79443f05b7bb6f0d8e  navigation/search.py
3523e6e53477430bc15b4d6ec895532a05b4fabcf8bc59a0e5ae6a919e8214db  navigation/planner.py
917dd0a79308d58a198035ec9f971f7d90bbbdbb9f88ae4453d27c55ac3276a0  navigation/depth_obstacles.py
004e302e52258b0b73bcc4e2d613e099256617c2c2bd1491eb68d486bf530e1b  perception/tabletop.py
c4d362b84dff3dd94a2691e62f36157afed0e2662ca9838d9c8dc945ce9d9d63  perception/placard.py
ac366295d8b06be0af1bd1154369b4c037766db868038f976fa5e271c726d957  perception/detectors.py
47728e0adc72824311dde9cf6ee738681348cd8942603ad6728148756be8d1ae  perception/geometry.py
7b251f78cab063132ea140b91c4997f30c833462991c78b4b1ba9daa425a8e21  sim/k1_observation.py
73e43b6827665d488a81302ab7aa68aa5c7359ce15f2bc48c96cf0a74a774610  experiments/claude-20261017T2008Z-k1-camera-autonomy-diagnostic/k1_autonomy_trial.py
```

## Corrections (2026-10-17T20:16:43+00:00, after Codex review 20:15Z)

The original text above is kept unchanged; these corrections take precedence.

1. **Videos are accelerated (~4×).** `evaluator.mp4` and `robot_camera.mp4` record one frame every
   ~0.4 s of sim time (frames are written on alternating 5 Hz camera ticks, `int(t·5)` even), but
   the writers were set to 10 fps. They play about 4× faster than simulated time. They're kept
   unmodified, and **must be captioned "accelerated ~4×"** if shown.
2. **Exact frame timestamps were recovered, not estimated.** The capture rule is deterministic, so
   replaying it over each trial's own `trajectory.csv` time column yields every frame's sim time.
   The count matches the MP4 frame count exactly for both views in all trials (A 50, B 54, C 300).
   They're written to `trial-*/frame_times.csv`.
3. **Real-time derivatives** `trial-*/evaluator_realtime.mp4` and `trial-*/robot_camera_realtime.mp4`
   are derived only from the original frames: each is held until the next frame's sim timestamp, at
   10 fps. They're new files with their own hashes below; prefer these for presentation.
4. **The final 2 s standing hold is not continuously recorded.** In A and B, after DELIVERED the
   harness commanded zero velocity for 2 s. Those steps aren't in `trajectory.csv`, the videos, or
   the peak-tilt metric; only `evaluator_final.png`, `robot_camera_final.png` and `sim_time_s` include
   them. "Stable stop" here means the executive's stability check before DELIVERED (measured speed
   ≤ 0.03 for 1.5 s, inside the recorded trajectory). The extra hold is **not** a continuous
   stable-stop recording. Trajectories end at 19.6 s (A) and 21.2 s (B), vs reported sim_time 21.6 s
   and 23.2 s.

New artifacts (sha256):
```
ec0c71aa758c8e3e7e23d9867d5a3634a4f6be167e64ea0093dfaa5e29c331fd  trial-A/frame_times.csv
976c5c9e012f71af4ca8241aa63ea3e48078b32aad027c655288e1843afae44d  trial-B/frame_times.csv
39028886d6880f8f64bceaa33d4442f5cc781e1771382c4d4a70e3c1ac46e274  trial-C/frame_times.csv
88015b0745a251f6309c30cd1b38e9cd6438f199feca980fd98454b2393ff10a  trial-A/evaluator_realtime.mp4
3810e8d850c8ae2ec9ea5a2a338e602aedc1738e501a238ae81f0d4e59280282  trial-A/robot_camera_realtime.mp4
97e9076ebd8d34e9ff301881b8387039e147712e563fcae7115247632ec7a040  trial-B/evaluator_realtime.mp4
99daa598182d01e6b52a646c1d4f2064a06504df0570d0481847ff6157a33ddd  trial-B/robot_camera_realtime.mp4
27da1a23d4f16fdeebd22ff9157614bade8dc6ec3c3ab05a79b896faa4320ddb  trial-C/evaluator_realtime.mp4
b74ca7a9be104875fb2ece81d569ef3dbf07f4cbd165802af604e85d07bbb972  trial-C/robot_camera_realtime.mp4
```
