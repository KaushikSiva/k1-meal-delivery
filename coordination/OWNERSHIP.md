# Ownership — shared checkout

Codex bootstrapped the instruction/status placeholders before Claude began. After bootstrap, each agent owns its own coordination files.

| Owner | Exclusive edit paths | First deliverable |
| --- | --- | --- |
| Codex | root files; docs/ARCHITECTURE.md; docs/ROADMAP.md; docs/EVALUATION.md; docs/RESOURCES.md; docs/hardware/; contracts/; sim/; training/; deployment/; evaluation/; tools/; tests/integration/; tests/evaluation/; tests/sim/; coordination/CODEX_*.md; coordination/OWNERSHIP.md | Project/bootstrap checkpoint, evidence protocol, K1/simulator readiness audit |
| Claude | autonomy/; perception/; memory/; navigation/; vla/; docs/autonomy/; tests/autonomy/; coordination/CLAUDE_STATUS.md; coordination/CLAUDE_HANDOFF.md; coordination/CLAUDE_LOG.md | Sensor-driven search/memory design and executable CPU baseline with labeled software tests; VLA data/action proposal |

No simultaneous edits to the same path. New paths outside these allocations must be claimed and agreed through handoffs before editing. Results under experiments/ use unique agent-prefixed run directories; results remain immutable after publication.

Codex maintains shared contracts after Claude review. Claude may independently draft proposed schemas under docs/autonomy/. No assumed compatibility until integration tests pass.

Codex handles all Git mutations in this shared checkout. Claude's ready-for-integration handoff must name exact files, test commands, limitations and whether editing those paths is frozen. Codex acknowledges the resulting commit in CODEX_HANDOFF.md.

Five-minute status updates are local communication. GitHub is checkpoint storage, not a substitute for checking the shared files during active collaboration.
