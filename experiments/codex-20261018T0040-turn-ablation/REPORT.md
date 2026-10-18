# Turning failure is present in the empty carrying posture

Twelve actual MuJoCo development probes compared the original unloaded controller, empty carrying posture, loaded carrying posture with nominal-arm actor observations, and loaded posture with actual-arm actor observations. Each requested 2s settling,4s yaw command,2s stop. Commands and conditions were frozen before execution. No GR00T, PPO, navigation or privileged actor velocity input.

| Condition | Yaw request | Maximum translation | Final speed | Measured yaw change |
| --- | ---: | ---: | ---: | ---: | ---: |
| stock_unloaded | +0.00 rad/s | 0.010 m | 0.000 m/s | 0.005 rad |
| stock_unloaded | -0.18 rad/s | 0.112 m | 0.002 m/s | -0.858 rad |
| stock_unloaded | +0.18 rad/s | 0.124 m | 0.003 m/s | 0.892 rad |
| empty_carry_posture | +0.00 rad/s | 0.069 m | 0.001 m/s | 0.001 rad |
| empty_carry_posture | -0.18 rad/s | 1.671 m | 0.315 m/s | -0.660 rad |
| empty_carry_posture | +0.18 rad/s | 1.705 m | 0.386 m/s | 0.701 rad |
| loaded_nominal_arm_obs | +0.00 rad/s | 0.074 m | 0.000 m/s | 0.003 rad |
| loaded_nominal_arm_obs | -0.18 rad/s | 1.787 m | 0.405 m/s | -0.653 rad |
| loaded_nominal_arm_obs | +0.18 rad/s | 1.698 m | 0.382 m/s | 0.668 rad |
| loaded_physical_arm_obs | +0.00 rad/s | 1.824 m | 2.143 m/s | not reached |
| loaded_physical_arm_obs | -0.18 rad/s | 1.824 m | 2.143 m/s | not reached |
| loaded_physical_arm_obs | +0.18 rad/s | 1.824 m | 2.143 m/s | not reached |

The original unloaded actor turned with0.112/0.124m drift and stopped below0.003m/s. Empty hands held in carrying posture drifted1.671/1.705m and kept moving after two seconds of zero command. The loaded condition was similarly poor. This establishes that GR00T and physical payload mass are not necessary for the drift; it does not identify one specific arm/gain/initialization cause, because the stock and carry setups differ in several respects.

Exposing actual carrying-arm encoders to the unadapted walking actor caused the same fall at1.56s in all three planned command conditions, before the move phase. These are three repeats of the same settling trajectory, not three independent yaw failures. Payload dropped. The nominal-arm ablation remains explicit and is not silently removed.

The empty-carry control sets supported-load feedforward to zero and translates the free payload bodies100m away. The robot never touches them; their fall is irrelevant to the empty-hand motion diagnostic. Loaded trials retain the physical hand seats and cup holder, no weld/torso bracket. Actor nominal-arm ablation does not alter actual telemetry.

Validation: existing hand-controller/residual tests3 passed. The new constructor defaults reproduce both prior baseline ±0.18rad/s trajectories bit-for-bit over400 control steps each. Simulation only; neither this ablation nor an in-place turn establishes camera-guided delivery or hardware readiness.

Next experiment: fresh PPO residual with quadratic velocity/yaw error penalties and explicit non-hand support penalty. Keep v1 reward as default, retain all failures, and evaluate the new checkpoint against the unchanged development protocol. These diagnostics inform the reward and cannot be called held-out evaluation. The live Isaac GUI remains unchanged.
