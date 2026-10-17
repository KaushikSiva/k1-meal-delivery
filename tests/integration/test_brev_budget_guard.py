import unittest
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

from tools.brev_budget_guard import find_instance, run


class BudgetGuardTests(unittest.TestCase):
    def test_selects_only_explicit_name(self):
        target = {"name": "k1-check", "status": "running"}
        self.assertEqual(find_instance({"workspaces": [{"name": "other"}, target]}, "k1-check"), target)
        self.assertIsNone(find_instance({"workspaces": None}, "k1-check"))
        self.assertIsNone(find_instance({"workspaces": [target]}, "other"))

    def test_ambiguous_name_refused(self):
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            find_instance({"workspaces": [{"name": "k1-check"}, {"name": "k1-check"}]}, "k1-check")

    def test_deadline_stops_only_target_and_verifies_terminal_state(self):
        def result(status):
            return subprocess.CompletedProcess([], 0, json.dumps({"workspaces": [
                {"name": "unrelated", "status": "running"},
                {"name": "k1-check", "status": status}]}), "")
        with tempfile.TemporaryDirectory() as tmp, patch("tools.brev_budget_guard.subprocess.run") as call, \
                patch("tools.brev_budget_guard.time.sleep"), patch("builtins.print"):
            call.side_effect = [result("running"), subprocess.CompletedProcess([], 0, "", ""), result("stopped")]
            state = Path(tmp) / "state.json"
            run("brev", "k1-check", "2020-01-01T00:00:00+00:00", state)
            self.assertEqual(call.call_args_list[1].args[0], ["brev", "stop", "k1-check"])
            self.assertEqual(json.loads(state.read_text())["state"], "verified_stopped")


if __name__ == "__main__":
    unittest.main()
