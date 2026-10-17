# Real hand-contact carrying in the Isaac café

**Attempt03 passed the15s scripted development carry:**2.193m forward, no drop or fall, maximum payload shift8.038mm, maximum tray tilt4.369°, final robot speed0.01850m/s. Peak arm torque7.391Nm, below the original14Nm limits. The longest contact loss was6ms per hand; contact was measured at500Hz against all23 robot bodies. No body other than the original terminal left/right hand links contacted the tray.

The tray is a separate free PhysX rigid body with gravity, friction, mass and inertia. It has physical raised rims, underside support seats and a cup holder; the box and can are also free rigid bodies. There is no torso bracket, fixed tray joint, invisible support, imposed trajectory or body-position update during rollout. Initialization assumes a person preloads the tray. Every subsequent motion is integrated by PhysX. Robot mass19.666kg, tray0.68kg, box0.8kg, sealed can0.5kg. Material friction0.7 is an assumption, not a physical measurement.

The frozen official K1 walking actor receives telemetry and a scripted0.4m/s command from2–13s. Its arm features are explicitly replaced with nominal arm positions/zero velocities. Actual arm motors execute a fixed IK-derived carrying pose with80/3PD gains and model-based gravity/load feedforward, saturated at14Nm. MuJoCo computes feedforward from measured encoders/attitude; it does not integrate the rendered robot or payload. No old torso-trained PPO residual or VLA controls these trials. Camera-guided loaded delivery and hardware performance remain unverified.

## Footage and verification

`attempt03/evaluator.mp4` and `attempt03/robot_camera.mp4` are continuous15s,375-frame recordings at25fps, with no skipped simulation time. The evaluator is a fixed wide café view; the head camera is attached to the official optical frame. Actual RGB is rendered by Isaac; no generated or composited success frames are used. The Domino’s-inspired printed packaging and Coke wordmark use the documented visual assets under sim/assets/payload/. The payload appearance shell itself adds no collision geometry; separate physical tray rims and support seats are present.

All14 downloaded artifacts matched hashes in attempt03/manifest.json. Exact hand-specific sources were recovered from saved source archives and independently matched against the manifest; they are retained under attempt03/source. Raw MP4s are local/ignored, with hashes committed. Remote location: `/home/ubuntu/workspace/k1-runtime/evidence/hand-isaac-03` on the authorized Brev L40S.

Attempt01 failed before simulation because its launcher referenced an absent uv path. Attempt02 failed on an invalid USD component path containing a minus sign. Attempt03 corrected the path spelling; it did not modify physical geometry for the successful result. These failures are preserved separately. The earlier MuJoCo model was tuned in attempts01–09; this cross-simulator run used the frozen development thresholds in evaluation/HAND_CARRY_PROTOCOL.json. One transfer and a deterministic repeat cannot establish reliability.


Attempt04 repeats the same physical setup with a closer following evaluator
camera and lower initial closeup. Root and payload/contact CSVs are byte-identical
to attempt03; all outcome metrics are identical. All14 downloaded artifact hashes
matched; the four hand-specific source snapshots matched the recorded hashes.
The repeated video is not an independent robustness trial. The tracking camera
uses evaluation-only root position and never controls the robot.

For the demo, use `attempt04/evaluator.mp4` (close following view) or
`attempt03/evaluator.mp4` (wide fixed view). Both have corresponding
`robot_camera.mp4` recordings. Each is continuous15s at25fps; the films record
actual simulated motion with gravity and contact, not pose animation.
