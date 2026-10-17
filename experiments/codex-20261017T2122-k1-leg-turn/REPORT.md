# Leg estimator turning diagnostic

Height RMSE was 0.002393 m; velocity RMSE was (0.055740, 0.028864) m/s and maximum planar error was 0.098346 m. This single turning diagnostic does not establish translation accuracy: the paired forward-walking trial failed. The manifest passed field refers ONLY to gyro heading.

Actual unloaded K1 in MuJoCo, unchanged official walking actor. The 20-second protocol is two seconds standing, 16 seconds moving at a 0.35 command, then two seconds stopping. The command is yaw rate for turning and forward speed for walking. No payload or VLA is involved.

Estimator input is native body gyro and named joint encoders; absolute free-base pose and velocity are evaluation-only. Initial world yaw 0.7 rad is setup/evaluation-only, while the estimator starts at the identity with an explicit level-reference assumption. Gyro noise is explicitly sampled at 0.005 rad/s standard deviation with 0.0015 rad/s z bias; encoders are ideal. These are assumed simulation sensor properties, not calibrated hardware uncertainty.

Leg height/velocity, where recorded, use a separate kinematic model with a flat-floor and stance-foot assumption, without physical contact truth. Only the provisional height estimate is used for subsequent camera extrinsics. No validated translational odometry claim follows from the height result.

Exact executed source hashes and raw CSV hashes are in manifest.json. Raw recordings remain locally in this directory but are excluded from Git. The verified historical source archive is `runs/leg-50hz-source.tar.gz`. These numerical diagnostics have no camera recording; subsequent navigation experiments supply actual RGB-D and continuous video.
