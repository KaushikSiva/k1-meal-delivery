# Four prospective loaded-navigation conditions

The fixed hand-carry profile completed **3 of 4** new start/target conditions. All four were specified before execution in protocol.json, and all used the immutable cbb4264 source snapshot and committed localizer. No controller changes were made between conditions. These four configurations do not establish a broad reliability rate or hardware performance.

| Condition | Result | Maximum pose error | Maximum payload shift |
|---|---|---|---|
| Start y−0.5m, yaw+0.12rad | Pass |9.22cm|4.01mm|
| Start y+0.5m, yaw−0.12rad | Fail:60s timeout with wall contact |108.92cm|11.80mm|
| Target x3.5m,y−0.35m | Pass |5.88cm|3.86mm|
| Target x4.5m,y+0.35m | Pass |11.49cm|5.06mm|

All three passes satisfied14 independent navigation, contact, tilt, effort and stable-stop checks. The failed condition had496 room-contact physics steps,13.66° peak tray tilt,14Nm peak arm effort, and brief tray contact with non-hand arm links. The load did not drop, and the robot did not trigger the fall threshold, but it did not complete the task. It must not be presented as a successful hands-only delivery. Localization drift and the resulting path/control behavior need further investigation.

The physical tray, pizza-box proxy and sealed-can proxy are free bodies. A physical cup holder and underside hand seats are present. Nominal arm observations in the frozen walking actor, torque-limited arm PD/load feedforward, the known-load depth self-filter and fixed0.5 command-to-translation prediction prior are declared in the previous integration report. No VLA or trained PPO residual was used.

All raw artifact hashes were verified against each manifest. Ignored continuous evaluator/head videos are retained locally. These conditions vary start pose, gyro-noise seed and target position, but not room dimensions, clutter, payload mass, surface friction or lighting. Further evaluation must cover those dimensions before a deployment claim.

Reproduce using evaluation/run_loaded_navigation.py with an immutable source checkout and evaluation/LOADED_NAV_VARIATION_PROTOCOL.json. The supplied floor plan and initial-pose prior are operator information; simulator pose is evaluation-only.
