"""Audit scripted MuJoCo diagnostics; never infer delivery success from walking.

Velocity is an evaluator-only finite difference of world position, transformed
using yaw only when available. The legacy trace has no yaw: its tracking error is
explicitly a WORLD-X proxy, not measured body-frame velocity tracking.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def analyze(run_dir):
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    for name, artifact in manifest["artifacts"].items():
        path = run_dir / name
        if Path(name).name != name or path.is_symlink():
            raise ValueError("Artifact must be a regular file in the run directory")
        content = path.read_bytes()
        if len(content) != artifact["bytes"] or hashlib.sha256(content).hexdigest() != artifact["sha256"]:
            raise ValueError(f"Artifact hash/size mismatch: {name}")
    if "trajectory.csv" not in manifest["artifacts"]:
        raise ValueError("Trajectory is not covered by the artifact manifest")
    with (run_dir / "trajectory.csv").open(newline="") as handle:
        rows = [{key: float(value) for key, value in row.items()} for row in csv.DictReader(handle)]
    if not rows:
        raise ValueError("Empty trajectory")
    phases = {name: {"duration_s": 0.0, "dx_world_m": 0.0, "dy_world_m": 0.0,
                     "squared_speed_integral": 0.0, "squared_error_integral": 0.0}
              for name in ("initial_stand", "forward", "stop")}
    previous_t = 0.0
    previous_x, previous_y, _ = manifest["initial_position_m"]
    dt_expected = manifest["policy_dt_s"]
    for row in rows:
        if not all(math.isfinite(value) for value in row.values()):
            raise ValueError("Nonfinite trajectory data")
        t = row["sim_time_s"]
        dt = t - previous_t
        if dt <= 0 or not math.isclose(dt, dt_expected, abs_tol=1e-8):
            raise ValueError("Trajectory must contain consecutive policy steps")
        # Each row contains the command applied during the preceding interval.
        # Infer phase by interval start; tiny tolerance handles floating-point time.
        phase = ("initial_stand" if previous_t < 2.0 - 1e-8 else
                 "forward" if previous_t < manifest["duration_requested_s"] - 2.0 - 1e-8 else "stop")
        p = phases[phase]
        dx, dy = row["world_x_m"] - previous_x, row["world_y_m"] - previous_y
        p["duration_s"] += dt
        p["dx_world_m"] += dx
        p["dy_world_m"] += dy
        p["squared_speed_integral"] += (dx * dx + dy * dy) / dt
        p["squared_error_integral"] += (dx / dt - row["command_vx_m_s"]) ** 2 * dt
        previous_t, previous_x, previous_y = t, row["world_x_m"], row["world_y_m"]
    final = manifest["final_position_m"]
    if not (math.isclose(previous_t, manifest["elapsed_sim_s"], abs_tol=1e-8)
            and math.isclose(previous_x, final[0], abs_tol=1e-8)
            and math.isclose(previous_y, final[1], abs_tol=1e-8)):
        raise ValueError("Manifest endpoint differs from trajectory")
    for p in phases.values():
        duration = p["duration_s"]
        speed_integral = p.pop("squared_speed_integral")
        error_integral = p.pop("squared_error_integral")
        p["mean_world_vx_m_s"] = p["dx_world_m"] / duration if duration else None
        p["rms_world_xy_speed_m_s"] = math.sqrt(speed_integral / duration) if duration else None
        p["world_x_command_proxy_rmse_m_s"] = math.sqrt(error_integral / duration) if duration else None
    return {
        "evidence_kind": "audited_unloaded_scripted_locomotion_diagnostic",
        "run": run_dir.name, "termination": manifest["termination"],
        "artifact_hashes_verified": True, "trajectory_rows": len(rows),
        "delivery_success": None, "payload_stability": None, "collision_count": None,
        "velocity_method": "world-position finite differences; world-X command comparison is a proxy (no yaw trace)",
        "phases": phases,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(args.run_dir), indent=2, allow_nan=False))
