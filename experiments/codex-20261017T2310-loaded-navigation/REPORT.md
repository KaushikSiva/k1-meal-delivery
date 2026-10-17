# Camera-guided delivery with a free hand-supported tray

**Attempt05 completed the integrated loaded delivery.** Head RGB-D and noisy gyro/encoders drove localization, table detection, memory, navigation and the frozen walking actor while the tray remained physically supported by both hands. The executive declared DELIVERED at22.8s; an additional2s verified the stop. No simulator root pose, object label or payload state entered navigation observations.

Measured result: final root position(2.950,-0.076)m, maximum localization error7.15cm, no room contact/fall/drop, maximum payload shift3.801mm, tray tilt5.065°, peak arm torque8.211Nm against14Nm limits. Longest hand contact losses4ms/2ms; no other robot link supported the tray. During the last1.5s, maximum speed0.001119m/s and drift1.104mm. The table's front edge was0.650m ahead of the robot root (not the tray edge). All14 independently checked acceptance gates passed; see attempt05/score.json.

The task is an unnumbered table in a simple room, with an operator-provided floor plan and initial-pose prior. The tray, box and can are free rigid bodies, with physical underside support seats and a cup holder. This run uses arm PD/load feedforward and the original walking actor; neither the torso-trained PPO residual nor a VLA controls it. A sealed can is modeled, not fluid. Hardware remains unverified.

## Integration changes and failures

| Attempt | Change | Measured outcome |
|---|---|---|
|01|First loaded sensor integration|Pizza top detected as another table; stopped AMBIGUOUS_DESTINATION. Carry stable.|
|02|Known-load depth self-filter|Localization drift, NO_PATH, wall contact and drop at24.8s.|
|03|Conservative command guard; read-only localizer WIP snapshot|Drift persisted; wall contact and drop at25.78s.|
|04|Head pitch−0.2rad; fixed prediction scale0.5|Delivered with stable load and no collision.|
|05|Committed localizer;25fps recording|Same root and payload/contact CSVs byte-for-byte as04; all gates pass.|

The scale0.5 is an explicit prior from the earlier straight hand-carry test (~0.19m/s actual at0.4m/s command), not online simulator velocity. A higher camera angle improves visibility beyond the tray. The guard holds translations below0.30m/s and limits yaw to0.25rad/s; it never increases an executive speed request or bypasses uncertainty caps. These changes were development tuning, not a held-out reliability evaluation.04/05 are deterministic repetitions, not two independent successes.

The self-filter marks only measured depth points inside a configured carrying envelope as unknown, using head encoders and the camera transform. It preserves RGB and raw depth, uses no simulator object segmentation/pose, and does not fabricate the background. Raw depth and filtered depth are both retained in the NPZ frames. The carrying envelope and camera calibration remain assumptions requiring hardware verification.

## Evidence and reproduction

`attempt05/evaluator.mp4` and `robot_camera.mp4` are local ignored recordings:621 actual frames at25fps,24.84s of video covering simulated timestamps0–24.8s. Perception still runs at5Hz; control50Hz, physics500Hz. The following evaluator camera reads world pose only for framing. All run artifact hashes were checked. Exact changed source snapshots for05 match its manifest; the localizer is the committed version from d426607. Uncommitted Claude WIP was never included in a release; earlier exploratory runs retain its source hash and local snapshot reference.

Reproduce with the pinned MuJoCo environment:

```sh
sim/.venv/bin/python sim/run_k1_sensor_navigation.py --output runs/loaded-nav-new \
  --duration 60 --hand-carried --known-load-depth-mask --carry-command-guard \
  --walk-speed .4 --settle-seconds 2 --head-pitch -.2 --prediction-scale .5 \
  --video-fps 25 --tracking-evaluator
```

Acceptance was frozen before01 in protocol.json; later controller/observation adjustments are listed above. All five attempts are retained, including failed physical runs. This is a first integrated development pass, not varied-layout reliability, learned-controller benefit or hardware completion.

Manifest metadata correction: the inherited `protocol.payload` string says `none` in these five runs; `payload_present`, `protocol.hand_carried`, physical model and contact data establish the actual load. This string is corrected for future runs, with the executed sources preserved here unchanged.
