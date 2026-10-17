# Carrying-control plan and current evidence

Status at 2026-10-17T20:58Z: actual residual PPO completed 204,800 physics
transitions and 1,600 optimizer updates. The first matched café comparison
carried farther before dropping the drink (3.23 m vs 1.25 m); both failed.
See experiments/codex-20261017T2055-ppo-cafe-evaluation/REPORT.md.
The base walking model remains the unchanged official
`k1_walk.pt` (SHA-256 `2d860167ed827e8d44cd65abd4c27f474904352bcb98c0cfa97c078f63e2fea5`).

## Implementation sequence

1. Verify that the unchanged actor can run in Isaac with named joint mapping,
   500 Hz explicit PD and 50 Hz policy inference. Compare real imported mass,
   joint limits, armature, contacts and observed stability with the MuJoCo
   baseline. Preserve failures; do not train around an accidental importer bug.
2. Add an explicitly documented supported tray to the robot and dynamic payload.
   The initial candidate is a rigid torso bracket, not an invented grasp. This is
   a simulation fixture assumption requiring mechanical/operator review before
   hardware use. Existing café counter staging is not robot payload attachment.
3. Run an unchanged-policy loaded baseline and record tray tilt, object motion,
   contacts, falls, drops and stop speed. Freeze a versioned development/evaluation
   protocol before comparing learned checkpoints.
4. Implement vectorized real-physics rollouts and PPO carrying adaptation. Keep
   a distinct empty-scene training environment for throughput; evaluate in the
   realistic café separately. Photoreal rendering is not needed at every low-level
   control step, but physics and telemetry must remain real simulation outputs.

Steps1–3 now have actual Isaac evidence: corrected19.666kg unloaded model walked
15s; supported0.95kg fixture +1.3kg free payload baseline dropped the drink at
6.442s. Step4 completed a 100-iteration run with real resets and exported the residual
to CPU TorchScript. A first matched development comparison still dropped the
drink. Current fixture and thresholds are versioned in sim/k1_payload.json.
Next: repeat with a wider evaluator camera, quantify variability, and investigate
carrying improvements before integrating camera-guided loaded navigation.

## Candidate PPO design

A bounded residual in joint-target space around the frozen official actor is
an initial candidate. This trains a new residual policy; it does **not** update
or fine-tune the frozen actor's weights. Report that distinction explicitly.
Direct actor fine-tuning is a separate comparison after a stable baseline.

Candidate residual bound: ±0.08 rad on the twenty walking-policy joints, with
head joints controlled separately. This is a development choice, not a validated
hardware limit. Start at zero residual so the baseline is recoverable.

Actor observations should use joint positions/velocities, IMU-equivalent angular
velocity and projected gravity, requested velocity, previous actions and history.
Perfect world pose, true payload displacement and simulator contacts may inform
training rewards or an asymmetric critic, but must be labeled privileged and
must not silently enter the deployment actor.

Reward terms must separately log velocity tracking, upright posture, tray tilt,
payload displacement, action rate and energy proxies. Terminations include falls,
payload loss and episode timeout. A reward increase alone is not evidence of
better delivery: compare matched evaluation metrics and video.

## Protocol draft to finalize after attachment geometry exists

- Begin with sealed drink and box; no open-cup/spillage claim.
- Candidate payload: box0.8kg + drink0.5kg, matching current staging assumptions.
  Include the measured/modelled tray and bracket masses rather than treating the
  support as massless. Dimensions/mass/friction must be stored in the actual config.
- Development starts/seeds are separate from final held-out layouts/seeds.
  Do not call current café captures held out; they have already informed development.
- Evaluate baseline and learned residual with identical requested velocities,
  payloads, friction settings, durations and starts. Include low-speed cases because
  the MuJoCo baseline showed a command deadband. Keep timeout/fall/drop denominators.
- Freeze exact numerical success thresholds before the matched comparison.
  Report raw tilt, displacement, speed and time as well as threshold outcomes.
- Save initial/final weight hashes, optimizer steps, genuine environment steps,
  learning curves, random seeds, package versions and compute time. A changed
  checkpoint hash without recorded optimizer/rollout evidence is insufficient.

## VLA work remains separate

No VLA fine-tuning has started. The bounded subgoal interface and recorder are
software components, not a trained vision-language-action model. Need a verified
base model, action/image compatibility, actual camera/action demonstrations,
explicit privileged-label accounting and held-out evaluation. The three unloaded
placard diagnostics alone do not establish a suitable training dataset.
