# Loaded pure-yaw diagnostic: substantial unintended translation

The hand-carry baseline does not reliably turn in place. Seven8s MuJoCo probes used the same initial pose (x0,y0.5,yaw−0.12), 2s settling,4s pure-yaw command, then2s zero command. The yaw rates were frozen before execution. No navigation, vision, PPO or VLA controlled these probes. Ground-truth positions only measure the result.

| Yaw request (rad/s) | Maximum translation (m) | Final true speed (m/s) |
|---|---|---|
|0|0.0755|0.000019|
|−0.05|0.0755|0.00548|
|+0.05|0.0755|0.00565|
|−0.15|1.6674|0.4015|
|+0.15|1.5983|0.3822|
|−0.25|1.8027|0.3995|
|+0.25|1.7912|0.3826|

The small±0.05rad/s commands barely changed heading. Larger commands caused backward translation and failed to settle after zeroing the command. Peak tray tilt reached12.01°; some trials had brief contact between the tray and an elbow-pitch link. No payload dropped, but this is not successful hands-only carrying under all commands.

The right-offset navigation failure includes the same pattern: uncommanded backward motion during rotation, followed by command-only odometry missing that displacement. These probes isolate a carrying-control problem in addition to the localization weakness. Merely forcing smaller navigation commands would suppress needed motion; a controller that can actually track turns and stops is required.

The free tray, physical underside hand seats and cup holder are unchanged. Arm PD/load feedforward and the frozen actor's nominal-arm observation ablation are active. Source and trajectory hashes are retained. These are diagnostic configurations, not held-out performance or hardware evidence.
