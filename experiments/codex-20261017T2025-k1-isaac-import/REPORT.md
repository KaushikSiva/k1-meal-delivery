# K1 import into the Isaac café — nominal PD failure retained

The official pinned K1 URDF imported with all 22 expected joint names and its
RealSense optical link intact. The actual GPU render is in
[k1-import-03/frame-0200.png](k1-import-03/frame-0200.png).

Three attempts:

1. Failed before import: Isaac Lab's application did not enable the camera
   extension. Fixed by enabling `isaacsim.sensors.camera` explicitly.
2. Converted the URDF but failed articulation initialization: an integer initial
   joint-velocity value was assigned into a float tensor. Explicit float values
   corrected the configuration.
3. Simulated under gravity with an unfixed base, nominal joint targets and
   implicit PhysX PD using pinned walking gains. It **fell at 1.472 simulated
   seconds**, reaching 60.23 degrees tilt. Initial root height was 0.57 m; no
   walking actor or payload was used. This is import/contact evidence, not a
   standing or delivery success.

Manifests preserve each attempt's exact code/config hashes. Raw converted USDs
remain remotely under `/home/ubuntu/workspace/k1-runtime/evidence/k1-import-*/`;
logs, exit files and shutdown-recovery audit are retained locally under ignored
`runs/brev-k1-20261017/k1-import-audit/`. All downloaded PNG/trajectory hashes were
verified against their manifests.

After attempt 03 wrote its finished manifest, native application shutdown stayed
active for over two minutes. The completed process was terminated with a recorded
SIGTERM; this did not stop the GPU VM. Its shell exit is not a clean success.
Future batch jobs use the documented immediate-close option after saving evidence.

The next diagnostic uses the unchanged official actor, explicit PD and the
pinned MJCF armature values. URDF-to-PhysX dynamics still require comparison with
MuJoCo, including total mass, contacts, actuator behavior and sensor geometry.
No PPO/VLA fine-tuning or payload carrying has occurred.

Subsequent walk03 mass audit found the unmerged empty camera links were assigned
1 kg each by PhysX, adding 2 kg relative to both source models (19.666 kg).
Attempt03 used the same unmerged import configuration, so its fall also has this
model-mismatch limitation. The next corrected baseline merges fixed massless
links and restores the optical frame without a dynamic body.
