# SmolVLA closed-loop development comparison

The frozen four-configuration comparison completed all eight runs. Executive-only passed **2/4**; the trained SmolVLA adapter passed **2/4**. This pilot establishes **no overall delivery improvement**.

| Configuration | Executive | SmolVLA |
|---|---|---|
| Prior validation00 | Timeout | Pass |
| Prior validation01 | Timeout | Timeout |
| New layout00 | Pass | Timeout |
| New layout01 | Pass | Pass |

These are unloaded MuJoCo trials with real rendered head RGB, encoder/gyro state, sensor-derived localization and one follower owning actuation. Perfect simulator state scores outcomes only. Measured inference latency gates proposal availability; the bounded adapter rejects expired/occupied subgoals and gives safety/executive final approach precedence. Four layouts are too few for reliability claims. Localization drift remains substantial; the worst executive trial reached3.12m error. No falls or room contacts were recorded in this comparison. One failed executive trial exceeded the tilt limit.

Protocol was frozen at22:19UTC before attempt02 started22:25UTC. Two configurations reuse prior collection/validation conditions and two are new; this is not a final held-out evaluation. The new-layout00 VLA trial physically stopped near the target but did not reach the required executive DELIVERED state, so it remains a failure. No success criteria were relaxed.

Checkpoint ca7e0eb430bc5896ee0639a880a3cef05f4fb0a684bb72a7c4f57ecce1907f53 had200 training updates on3 episodes/262frames before this evaluation. No optimizer ran during comparison. Actual VLA calls, control ownership, rejection reasons, latency, per-trial checks and artifact hashes are in comparison.json and each manifest.

Attempt01 failed preflight because the remote pinned booster_assets package initializer was absent; no trial ran. Its log is retained. Attempt02 included that initializer. Raw video, NPZ and traces remain at `/home/ubuntu/workspace/k1-runtime/evidence/vla-comparison-02` on the authorized Brev VM; compact reviewed evidence is in local `runs/vla-comparison-02-review`. Hardware and loaded delivery remain unverified.
