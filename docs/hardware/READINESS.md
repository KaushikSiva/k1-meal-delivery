# Hardware and simulator readiness — initial audit

## Verified local facts

The current `python3` interpreter is Python 3.13.7 on an arm64 Mac. In this interpreter, MuJoCo, PyTorch, Isaac Lab, Isaac Sim, NumPy and pytest are not installed. `nvidia-smi` is not on PATH. This is an inventory of this interpreter and PATH, not proof that no other environments or remote GPUs exist. See local-environment.json.

No K1 is currently available according to the user. No Crusoe GPU VM or budget has been verified. Full Isaac Sim execution and policy training have not started. CPU-only contracts, tests and experiment tooling can proceed now.

## You.com verification

The user supplied a You.com credential, stored in ignored `.env` with owner-only file permissions. A real Web Search API request succeeded and returned three source leads. See you-k1-specifications-search.json for the request, provider, timestamp and source URLs. No credential is recorded there.

The K1 product search result lists multiple compute variants. Do not choose a runtime budget from a single TOPS number without identifying the actual robot configuration. The search also returned a T1 page; it must not be used as K1 evidence.

Tray payload capacity, stable carrying posture, attachment design, camera calibration/data access, command timing, and exact firmware/model compatibility remain unverified. No mass, friction, carrying capacity or success percentage is invented.

## Next evidence to obtain

1. Retrieve and inspect official K1 specification and deployment sources through You.com research; retain the model/variant distinction and dates.
2. Pin compatible Booster asset/training/deployment revisions. Identify an actual usable baseline checkpoint and its license, observation/action definitions and model version.
3. Verify a Linux NVIDIA VM suitable for the exact Isaac Sim stack. Record price/capacity and authorized budget before provisioning.
4. Load the real K1 asset, step the simulator and validate sensor/action wiring. Then test a baseline controller and capture genuine outputs.
5. Prepare read-only arrival-day telemetry and mapping checks before any physical actuation.

Readiness state: preparation in progress. No simulated or physical carrying capability has been demonstrated.
