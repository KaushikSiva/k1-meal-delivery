# Instructions for Codex and Claude

Read GOAL.md, coordination/OWNERSHIP.md, both STATUS files and the other agent's HANDOFF file before beginning work. The user values real company progress over a polished hackathon demo.

## Coordination and file ownership

- Use this shared checkout on main. Do not switch branches, reset, stash or clean the shared working tree.
- Edit only your assigned paths. Before starting, claim the task and exact paths in your own STATUS file and read the other agent's claims. Ownership changes require a Markdown handoff and acknowledgement, not a unilateral timeout takeover.
- Each agent writes its own STATUS, HANDOFF and LOG files. Never overwrite the other's updates. Bootstrap placeholders are explicitly labeled.
- Shared contracts, root configuration and integration belong to Codex. Claude proposes shared changes in coordination/CLAUDE_HANDOFF.md. Independent work should continue while awaiting an answer.
- Codex is the sole Git integrator in this checkout. Claude does not stage, commit, pull, merge or push here. When ready, Claude lists exact stable paths and tests in its handoff, then stops editing those paths until Codex acknowledges the commit.
- Codex commits only reviewed paths. Never use blanket staging when a teammate is writing. Do not include incomplete teammate work. If isolated worktrees are needed later, agree on a shared coordination location first.

## Five-minute update contract

- Refresh your own Markdown STATUS at least every 300 seconds of active work, and on each major result, failure, ownership change or handoff.
- Include UTC timestamp, state, task, claimed paths, actual evidence, blockers, next action and last teammate update read.
- Append significant results to your LOG; keep history instead of replacing previous outcomes.
- Check elapsed time between tool calls. Start long jobs asynchronously and poll at intervals that allow real status updates. Do not leave a blocking tool call longer than the heartbeat interval.
- No fake heartbeat daemon: refreshing a timestamp without inspecting work is not an agent progress update. When the agent stops, mark it idle or waiting. No claim of five-minute updates while no agent process/turn is running.

## Engineering and evidence

- Do useful work autonomously inside the authorized project. Do not provision paid resources without a known authorized budget or actuate hardware before applicable physical checks and an operator are in place.
- Use You.com for new real-world specification/asset research. If credentials are absent, record the blocker and continue independent work. Label older references as pre-project research.
- Distinguish planned, implemented, locally tested, simulated, trained and hardware-verified. Unit tests and mocked data are software evidence, not robotics performance.
- No simulator-only observation may silently enter the deployment actor. Privileged training inputs must be labeled and isolated from deployed inputs.
- Use meaningful tests for interfaces, evidence accounting and control behavior. Record failures and regressions. Do not optimize a final test set or silently change success criteria.
- Never log secrets or commit weights/raw video/datasets. Keep artifact hashes, provenance and storage references. No invented screenshots, trajectories, training curves or success rates.
- Push at coherent checkpoints after validation and a staged-diff review. Existing user authorization covers these private GitHub checkpoint pushes.
