import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from evaluation.analyze_locomotion import analyze


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.trace = self.root / "trajectory.csv"
        with self.trace.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["sim_time_s", "world_x_m", "world_y_m", "command_vx_m_s"])
            w.writerows([(1, 0, 0, 0), (2, 0, 0, 0), (3, .1, 0, .2),
                         (4, .2, 0, .2), (5, .2, 0, 0), (6, .2, 0, 0)])
        self.manifest = {"initial_position_m": [0, 0, .6], "final_position_m": [.2, 0, .6],
                         "policy_dt_s": 1, "duration_requested_s": 6, "elapsed_sim_s": 6,
                         "termination": "completed_requested_duration"}
        self.save()

    def save(self):
        data = self.trace.read_bytes()
        self.manifest["artifacts"] = {"trajectory.csv": {
            "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}}
        (self.root / "manifest.json").write_text(json.dumps(self.manifest))

    def test_phase_intervals_and_unknown_task_metrics(self):
        result = analyze(self.root)
        self.assertAlmostEqual(result["phases"]["forward"]["mean_world_vx_m_s"], .1)
        self.assertAlmostEqual(result["phases"]["forward"]["world_x_command_proxy_rmse_m_s"], .1)
        self.assertEqual(result["phases"]["stop"]["rms_world_xy_speed_m_s"], 0)
        self.assertIsNone(result["delivery_success"])
        self.assertIsNone(result["collision_count"])

    def test_modified_artifact_is_rejected(self):
        self.trace.write_text(self.trace.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "hash/size"):
            analyze(self.root)

    def test_missing_steps_are_rejected_even_with_valid_hash(self):
        self.trace.write_text(self.trace.read_text().replace("3,0.1,0,0.2\n", ""))
        self.save()
        with self.assertRaisesRegex(ValueError, "consecutive"):
            analyze(self.root)

    def test_manifest_endpoint_must_match(self):
        self.manifest["final_position_m"][0] = 99
        self.save()
        with self.assertRaisesRegex(ValueError, "endpoint"):
            analyze(self.root)

    def test_nonfinite_trace_is_rejected(self):
        self.trace.write_text(self.trace.read_text().replace("3,0.1,0,0.2", "3,nan,0,0.2"))
        self.save()
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            analyze(self.root)


if __name__ == "__main__":
    unittest.main()
