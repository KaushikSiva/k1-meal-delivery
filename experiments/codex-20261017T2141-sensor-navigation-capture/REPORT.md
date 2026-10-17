# Captured RGB-D reproduces a false table at the wall corner

This instrumentation repeat exactly reproduced the first sensor-estimated
navigation failure: ambiguity at 9.6 s, termination at 10.98 s, maximum XY
localization error 0.09741 m and final error 0.02482 m. It is not an independent
randomized trial. The setup and limitations are described in
[the initial report](../codex-20261017T2140-sensor-navigation/REPORT.md).

At 9.6 s the estimated robot pose was (1.6491, -0.0443, 0.0497 rad). Scene memory
contained the real table at (3.979, 0.027, 0.749 m), confidence approximately 1.0,
and a new false table at **(6.532, -2.529, 0.746 m)**, confidence 0.612 from one
sighting. The physical table is centered at (4,0); the far walls lie at x=7 and
y=-3. This evidence points to a false wall-corner detection, not a second table.

Hypothesis, not yet proven: a global height peak from the real tabletop also
selects vertical-wall slices at that height; their corner spans both horizontal
axes and survives the detector's width checks. The perception owner received
the exact frame for a targeted regression. The ambiguity guard remains intact.

Reproduce the detector input from `rgbd-0048.npz`: RGB, depth, T_base_camera,
estimated pose/covariance and timestamp are all stored. Intrinsics are 640x480,
58-degree vertical FOV. Raw captures and localization.json are excluded from Git;
their hashes are in manifest.json. Raw data remain in this local experiment
directory. Executed source is preserved in
`runs/sensor-navigation-capture-source.tar.gz`, with matching manifest hashes.

Both continuous videos contain 55 frames at 5 fps, timestamps 0–10.8 seconds.
They are actual recordings. No delivery, stable-stop or payload success is claimed.
