# Wider-camera repeat preserves both original failures

The evaluator camera was moved to show the full straight route. Robot, payload,
commands, physics and checkpoints were unchanged. Final recorded frames now
retain the robot and dropped drink, although foreground furniture can occlude
its feet. The evaluation camera is excluded from controller inputs.

The unchanged walking actor again dropped the drink at 6.442 seconds after
1.24631 m forward displacement. The final PPO02 residual again dropped it at
12.126 seconds after 3.22968 m. Both fail the existing stability protocol.
These deterministic repeats reproduce the earlier outcomes; they are not
independent randomized trials or evidence of broad repeatability.

The baseline and residual subdirectories contain exact manifests, real captured
frames and frame timestamps. Raw video/trajectory artifacts stay outside Git
with hashes in those manifests. Their remote root is
`/home/ubuntu/workspace/k1-runtime/evidence/k1-wide-pair01`; the downloaded archive
is `runs/brev-k1-20261017/k1-wide-pair01-evidence.tar.gz`. The corresponding source
archive contains the runner delta; unchanged dependencies are pinned by the
manifest hashes and preceding checkpoint 29e8727.

Final PNGs are the last frames actually recorded, not synthesized termination
frames. The manifests record their timestamps; the recording can precede the
physics termination by a fraction of one frame interval.
