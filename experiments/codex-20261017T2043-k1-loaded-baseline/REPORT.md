# Supported-payload baseline: drink dropped

Actual Isaac Sim café run, unchanged official walking actor, scripted velocity.
This is a failed carrying baseline, not a delivery. Scene assets: Poly Haven CC0.

The explicit fixture is a rigid torso bracket (0.35 kg) and tray (0.60 kg),
not a grasp. The free box is 0.80 kg and sealed rigid drink 0.50 kg. There is no
rim, cup holder, restraint or liquid simulation. Dimensions, friction assumptions
and development thresholds were set in sim/k1_payload.json before this run.
Imported robot-plus-fixture mass20.6160002kg and both object masses were checked.

The drink tipped, rolled/slid forward and dropped at6.442s, after1.246314m net
forward travel. Peak body tilt was3.381482degrees. The robot had not fallen;
termination was `payload_drop`. Peak payload tilt104.2543degrees and displacement
0.310774m reflect the drink failure. At the last50Hz sample (6.44s), box horizontal
displacement was0.02342m and drink displacement0.30996m. The box remained on the
tray. No successful stop or delivery is claimed.

Ten downloaded artifact hashes checked. Payload/root trajectories have322rows,
50Hz. Videos have161frames at25fps (6.44s); the final2ms before termination are
not represented in video or50Hz CSV. All physics steps contribute to reported
maxima. Visual review of evaluator-0125.png shows the tipped drink on the tray.

Original remote directory:
`/home/ubuntu/workspace/k1-runtime/evidence/k1-loaded-01`.
Local archive: `runs/brev-k1-20261017/k1-loaded-01-evidence.tar.gz`.
Exact source archive: `runs/brev-k1-20261017/k1-loaded-01-source.tar.gz`.
Weights and raw videos/trajectories stay out of Git. The café and payload are
development fixtures, not held-out or hardware-calibrated conditions.
