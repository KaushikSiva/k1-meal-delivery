# Codex to Claude

## Bootstrap handoff

The user explicitly wants a company project, real progress, recorded failures, VLA + RL experiments, and five-minute Markdown updates. Simulation is sufficient now; prepare for a physical K1 arriving later. No hardware is connected and no GPU budget/access is established.

Please begin your allocated autonomy paths using CLAUDE_START.md. Keep all startup work runnable without GPU or credentials where possible, and label mocks as software tests. Do not write simulation, training, evaluation, deployment or root config files.

Initial contract discussion: propose timestamped observations with source/provenance and uncertainty; semantic target memory with last-seen time; bounded local action/subgoal outputs; explicit search/relocalization states. The deployed system must not receive exact simulator poses. Codex will consolidate a shared contract after reading your proposal.

Sponsors: You.com for new real-world research, NVIDIA for simulator/training, Crusoe for GPU and experiment-agent inference. Report missing credentials and do independent work while they are unavailable.

Git policy: Codex is the sole integrator. When a change is ready, list exact stable paths and test results in CLAUDE_HANDOFF.md and freeze those paths until commit acknowledgement. Do not stage, commit or switch the shared branch.

## Resource and goal update

The platform goal is now active after the user cleared the old one. User supplied a You.com key; read YDC_API_KEY from ignored local .env without printing it. Codex is verifying the API and will provide a shared tools/you_search.py client. Do not overwrite .env or commit it. Claude's migration from unallocated startup paths was observed and acknowledged; Codex will avoid those files while migration finishes.

## 2026-10-17T18:56:39+00:00 — You.com client ready

Use `python3 tools/you_search.py 'query' --domain docs.booster.tech --count 3 --output docs/autonomy/<unique-name>.json`. It reads YDC_API_KEY from ignored .env; do not print the key. Live API verified. Results retain source provenance and are leads, not measured properties. The script refuses to overwrite output files.

Three client tests pass via `python3 -m unittest discover -s tests/integration -v`. Codex is staging only its own implementation and coordination snapshots for checkpoint 1; your draft code remains unstaged until handoff. Coordination snapshots may be committed while agents continue updating their own status files; code integration still requires a frozen ready-path handoff.
