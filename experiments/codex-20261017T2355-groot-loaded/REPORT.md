# GR00T500-update checkpoint: four loaded delivery conditions

**GR00T+executive3/4; executive-only3/4. No overall delivery improvement.** Both modes used the same four frozen start/target/gyro-seed conditions and carrying profile. The trained GR00T03 checkpoint supplied bounded subgoal proposals through the existing arbitration interface; the executive retained completion, uncertainty handling and stop authority. Physics used the same free hand-supported tray, box and can.

| Condition | Executive | GR00T+executive | VLA-owned control ticks |
|---|---|---|---|
|Start left|Pass|Pass|0|
|Start right|Fail|Fail|9|
|Target near left|Pass|Pass|27|
|Target far right|Pass|Pass|119|

The checkpoint hashes were verified before serving and recorded in every trial. Inference ran on the authorized L40S through a localhost SSH tunnel. Full-resolution raw RGB and the same16-value telemetry/memory vector were transmitted. Measured end-to-end inference delay was applied to simulated proposal availability; the0.6s freshness limit was unchanged. This is a synchronous simulation harness, not a real-time hardware runtime.

Transport latency was substantial: condition means ranged0.537–1.593s. All22 proposals in the first trial expired before use. Later conditions accepted some bounded proposals, but retained the same pass/fail pattern. There were no HTTP/model inference failures. A lossless PNG transport variant is being tested separately; this raw-transport batch is preserved as measured.

The comparison is against the previously recorded, immutable executive batch in ../codex-20261017T2340-loaded-variation/. No policy training or tuning occurred during these four episodes. Protocol, source snapshots, per-run metadata, artifact hashes and score files are included; raw videos, state arrays and proposal/control traces remain local ignored artifacts. The failed right-offset condition remains a failure; do not equate successful model calls with successful delivery.
