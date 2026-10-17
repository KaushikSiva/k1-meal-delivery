# Free tray supported by K1 hands — MuJoCo development

Attempt09 carried the preloaded free tray2.036m in15s and stopped; attempt10 repeated identical physics with per-step contact recording. Neither dropped the tray/payload nor fell. Maximum payload shift3.295mm, peak tray tilt7.195° (full500Hz measurement), final root speed0.01371m/s, peak arm torque7.158Nm against14Nm limit. The longest individual hand contact loss was4ms left /2ms right. No torso or other non-hand robot contact supported the tray.

Attempt10 meets the development thresholds frozen after attempt09. It is a deterministic instrumented repetition, not an independent reliability estimate. The checkerboard diagnostic video is in local `runs/hand-carry-10/evaluator.mp4` (25fps,15s, continuous). Café/Isaac transfer is evaluated separately.

All objects are real dynamic rigid bodies: tray0.68kg, pizza box0.8kg, sealed can0.5kg. The model has zero equality constraints, no welded tray, no torso support and no imposed body poses during rollout. Gravity is9.81m/s², assumed friction0.7. The tray has physical raised rims, a cup holder and visible underside handle seats resting on the original terminal hand colliders. A person is assumed to preload it; there is no pickup/placement action or fluid simulation.

The original frozen K1 walking actor drives legs. Arms use an IK-derived pose, PD80/3, model gravity/Coriolis and known payload load compensation through joint torques, with the original14Nm saturation. Nominal arm features replace the carry pose in the walking actor's observation as an explicitly documented ablation. Actual encoders, IMU and joint dynamics remain physical. Neither VLA nor the old torso-trained PPO residual is active. This is scripted velocity, not camera-guided delivery.

Failures are retained:01 renderer preflight failure;02 initial mesh penetration ejected tray;03–06 dropped the tray within0.75s while reach, initial foot height and load support were corrected.07 stood8s.08 stood15s despite a0.25m/s command;09/10 use0.4m/s and walk. These development adjustments are not a frozen evaluation set. Exact source copies are saved locally from09 onward; earlier runs retain available manifests/XML but do not all have independent source snapshots.

Physics is still an approximation: collision meshes, contact solver, friction and payload priors are uncalibrated against hardware. This report establishes a simulated hand-contact carry, not real robot performance.
