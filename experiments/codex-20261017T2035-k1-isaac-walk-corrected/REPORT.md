# Corrected-mass K1 walking in Isaac café

Actual Isaac Sim 5.1 / PhysX run on the authorized L40S, 2026-10-17.
Unchanged official walking actor; scripted velocity, unloaded, no vision guidance,
no fine-tuning and no delivery claim. Furniture/textures/HDRI: Poly Haven CC0.

The prior walk03 found two empty sensor links with unintended 1 kg masses.
This run merges fixed joints, recreates the optical frame as a nonphysical USD
transform, and asserts imported mass against the source URDF before inference.
The source and checkpoint hashes are in manifest.json; source archive is
`runs/brev-k1-20261017/k1-walk-04-source.tar.gz`.

- Imported mass: 19.6659995 kg versus source 19.666 kg; 22 joints verified.
- 15 simulated seconds, 750 actor evaluations; no fall termination.
- Commands: stand 2 s, forward 0.35 m/s for 11 s, stop command for 2 s.
- Net forward displacement: 2.9196377 m. Peak body tilt: 4.368461 degrees.
- Final root: (3.919638, -0.033718, 0.550044) m.
- Both continuous videos: 375 frames, 25 fps, exactly 15 s. Actual frame times
  are supplied; trajectory has 750 samples at 50 Hz.

All ten downloaded artifact hashes, timestamps, video metadata and trajectory
endpoint were independently checked. Converted USD files remain remote and are
hashed in the manifest. Raw videos/trajectory stay out of Git. Evidence archive:
`runs/brev-k1-20261017/k1-walk-04-evidence.tar.gz`; original remote directory:
`/home/ubuntu/workspace/k1-runtime/evidence/k1-walk-04`.

Visual review confirms the evaluator shows the articulated robot walking in the
café and the head camera now views the room, unlike walk03's incorrect view.
This is not yet numerical validation of moving-camera RGB-D extrinsics. Camera
intrinsics remain assumed. The evaluator camera is fixed and is not a robot
observation. No payload is attached, no obstacle navigation is exercised, and
the café remains a development scene, not a held-out evaluation.

The app exited cleanly after flushing artifacts using the installed SDK's
`close(wait_for_replicator=False, skip_cleanup=True)` option. Earlier failed
attempts and the mass-mismatch diagnostic are preserved separately.
