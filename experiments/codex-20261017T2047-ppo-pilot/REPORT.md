# First genuine residual PPO updates

Actual Isaac Sim / PhysX rollouts on the L40S, not a mock training curve.
Eight loaded K1 instances,128policy steps each:1,024transitions,1,280physics
ticks at500Hz, two PPO iterations and eight optimizer updates. Training loop
wall time5.413s excludes simulator startup/conversion. Seed7101.

This trains a NEW ±0.08rad residual around the unchanged official walking actor.
It does not fine-tune that actor or a VLA. Both actor and critic receive only
joint/IMU/command/history signals plus the previous residual. True velocity and
payload/root state are used only for rewards and terminations.

Independent checkpoint inspection verified:

- Actor parameter change L2:0.15815805; critic:0.36625218.
- Combined parameter change L2:0.39901325.
- Initial parameter SHA256:
  `a099e9fc4328f28cbadd0cfd0bc6b96c0ada14bf6ce67ea0e392a3f744be76ba`.
- Final parameter SHA256:
  `43db3102203be210c36c5532c133e9e0fb37fcdfb8032cfad94fe5d5163b5391`.
- Saved final checkpoint hash matches manifest; original actor hash unchanged.
- Two metrics rows account for exactly1,024transitions/eight optimizer steps.

This pilot lasts only2.56simulated seconds per instance: no episode completes,
and it does not test sustained carrying, dropping or reset behavior in physics.
Unit tests separately cover selective actor resets and terminal/timeout GAE.
No improvement, success rate or delivery claim is supported by this pilot.

Training occurs on a plain development floor with the same provisional supported
tray/free payload model, not in the rendered café. A longer32-instance run and
matched rendered evaluation are separate experiments.

Original remote: `/home/ubuntu/workspace/k1-runtime/evidence/k1-ppo-01`.
Weights (`initial.pt`, `final.pt`, iteration snapshots) remain there, outside Git.
Local evidence/source archives: `runs/brev-k1-20261017/k1-ppo-01-{evidence,source}.tar.gz`.
Manifest stores source, weight and parameter hashes; metrics.jsonl stores actual
training measurements. `optimizer_steps` in each metrics row is that iteration's
count; `optimizer_steps_total` is cumulative.
