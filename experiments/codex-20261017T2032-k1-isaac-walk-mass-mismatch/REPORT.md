# Isaac walking diagnostic — imported mass mismatch

The unchanged official K1 actor executed 750 steps at 50 Hz and completed
15 simulated seconds in the textured café. Script: stand2s, command0.35m/s
forward11s, stop2s. Net world-x displacement3.10644m; peak root tilt4.0752°;
no fall termination. No tray or payload attached, no vision guidance, no training.

**This is not a valid nominal-mass baseline.** PhysX assigned1kg to each empty
fixed camera link: actual total21.666kg versus19.666kg in both pinned source
models. The next attempt merges those links and asserts total mass before running.
The added mass is an importer defect, not a deliberate payload experiment.

**Camera failure retained:** visual review of robot_camera-0125.png shows floor
and the exterior boundary rather than the expected forward café view. Optical
transform integration needs verification. These images cannot establish correct
articulated perception or vision-guided delivery. The actor uses proprioception
and scripted velocity, so this camera defect did not feed its control inputs.

Both videos contain375frames at25fps (15s); actual simulation capture timestamps
are in frame_times.csv. PNG/video/trajectory hashes were independently checked
after download. Converted USDs remain remotely under
`/home/ubuntu/workspace/k1-runtime/evidence/k1-walk-03/converted/`.
Videos and trajectory remain locally available but ignored by Git.

Two prior attempts failed before actor inference: camera-frequency incompatibility,
then a float/double USD orientation mismatch. Their manifests/logs are retained
in the failed-attempt audit. Attempt01's initial walking_policy_executed=true flag
was set prematurely; its traceback proves no actor was constructed or run. Later
runners set that flag only after an actual inference and count actor_steps.

Furniture, floor textures and HDRI: [Poly Haven](https://polyhaven.com/) (CC0).
