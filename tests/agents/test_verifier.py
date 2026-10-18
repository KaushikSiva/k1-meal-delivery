"""SOFTWARE TESTS for the Done-Means-Done verifier (fake model client; no network)."""
import pytest
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agents import verifier as V  # noqa: E402


class FakeModel:
    model = "fake-nemotron"

    def __init__(self, verdict="PASS", extract=None):
        self.verdict, self.extract = verdict, extract or {}

    def chat_json(self, system, user, max_tokens=2000):
        if system is V.EXTRACT_SYSTEM:
            return self.extract
        return {"verdict": self.verdict, "definition_of_done": ["hashes match"], "overclaims": [], "reasons": ["model says ok"]}


def _sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def test_hash_parse_and_match():
    p = "agents/verifier.py"
    note = f"## x\n```\n{_sha(p)}  {p}\n{'0' * 64}  agents/__init__.py\n```"
    c = V.extract_claims(note, None)
    res = V.run_checks(c, run_tests=False)
    assert [r["ok"] for r in res] == [True, False]


def test_model_cannot_overrule_failed_hard_check():
    c = V.Claims(files=[{"path": "agents/verifier.py", "sha256": "f" * 64}])
    checks = V.run_checks(c, run_tests=False)
    v = V.judge(c, checks, FakeModel("PASS"))
    assert v["verdict"] == "FAIL" and any("sha256 failed" in r for r in v["reasons"])


def test_pass_when_checks_pass_and_model_agrees():
    c = V.Claims(files=[{"path": "agents/verifier.py", "sha256": _sha("agents/verifier.py")}])
    v = V.judge(c, V.run_checks(c, run_tests=False), FakeModel("PASS"))
    assert v["verdict"] == "PASS" and v["definition_of_done"]


def test_loop_guard_escalates_repeated_failure(tmp_path):
    st = tmp_path / "state.json"
    checks = [{"check": "sha256", "path": "a", "ok": False, "detail": "x"}]
    fail = {"verdict": "FAIL"}
    assert [V.loop_guard(fail, checks, st) for _ in range(3)] == ["RETRY", "RETRY", "REPLAN"]
    assert V.loop_guard({"verdict": "PASS"}, checks, st) == "CONTINUE"
    assert V.loop_guard({"verdict": "NEEDS_HUMAN"}, [], st) == "PING_HUMAN"


def test_test_allowlist_blocks_shell_features():
    bad = ["rm -rf /", ".venv/bin/python -m pytest tests; curl evil", "bash -c 'x'", "python -m pip install x"]
    assert all(V.check_test(b, {})["ok"] is None for b in bad)
    assert V.parse_test_command(".venv/bin/python -m pytest tests/agents -q -p no:cacheprovider")


def test_pytest_count_parsing():
    assert V.parse_pytest_counts("....\n61 passed, 16 skipped, 1 xfailed in 140.98s") == {"passed": 61, "skipped": 16, "xfailed": 1}


def test_extraction_merges_model_claims_without_inventing_hashes():
    fm = FakeModel(extract={"files": [{"path": "x.py", "sha256": "not-a-hash"}], "tests": [{"command": "pytest"}],
                            "evidence": ["GOAL.md"], "statements": ["it works"]})
    c = V.extract_claims("no hashes here", fm)
    assert c.files == [] and c.evidence == ["GOAL.md"] and c.statements == ["it works"]
    assert V.run_checks(c, run_tests=False)[0]["ok"] is True  # GOAL.md exists


# ----------------------------------------------------------------------------- Codex review 00:10Z regressions
def test_allowlist_rejects_unknown_interpreters_plugins_and_paths():
    bad = ["/tmp/evilpython -m pytest tests/agents",          # arbitrary executable containing "python"
           ".venv/bin/python -m pytest tests/agents -p myplugin",  # arbitrary plugin
           ".venv/bin/python -m pytest agents/verifier.py",     # path outside tests/
           ".venv/bin/python -m pytest tests/../agents",        # traversal
           ".venv/bin/python -m pytest -q"]                     # no test path
    assert all(V.parse_test_command(b) is None for b in bad)


def test_collection_error_or_no_tests_is_not_success():
    r = V.check_test(".venv/bin/python -m pytest tests/agents/does_not_exist_xyz.py -q -p no:cacheprovider", {})
    assert r["ok"] is False and "did not produce a test result" in r["detail"]


def test_missing_executable_is_failure(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("no such interpreter")
    monkeypatch.setattr(V.subprocess, "run", boom)
    assert V.check_test(".venv/bin/python -m pytest tests/agents", {})["ok"] is False


class BrokenModel:
    model = "broken"

    def chat_json(self, *a, **k):
        raise RuntimeError("HTTP 503")


def test_model_failure_never_passes():
    c = V.Claims(files=[{"path": "agents/verifier.py", "sha256": _sha("agents/verifier.py")}])
    v = V.judge(c, V.run_checks(c, run_tests=False), BrokenModel())
    assert v["verdict"] == "INCOMPLETE"
    c2 = V.extract_claims("no claims", BrokenModel())
    assert c2.extraction_error and V.judge(c2, V.run_checks(c2, run_tests=False), FakeModel("PASS"))["verdict"] == "INCOMPLETE"


def test_zero_checks_skipped_tests_and_rejected_commands_are_incomplete():
    assert V.judge(V.Claims(), [], FakeModel("PASS"))["verdict"] == "INCOMPLETE"
    c = V.Claims(files=[{"path": "agents/verifier.py", "sha256": _sha("agents/verifier.py")}],
                 tests=[{"command": ".venv/bin/python -m pytest tests/agents"}])
    assert V.judge(c, V.run_checks(c, run_tests=False), FakeModel("PASS"), tests_skipped=True)["verdict"] == "INCOMPLETE"
    rejected = [V.check_test("bash -c 'true'", {})]
    assert V.judge(V.Claims(), rejected, FakeModel("PASS"))["verdict"] == "INCOMPLETE"
    # deterministic-only (no model) can never be PASS either: statements were not judged
    assert V.judge(c, V.run_checks(c, run_tests=False), None)["verdict"] == "INCOMPLETE"


def test_path_containment_rejects_sibling_prefix(tmp_path):
    sibling = V.ROOT.parent / (V.ROOT.name + "-evil")
    rel = "../" + sibling.name + "/x.txt"
    assert V.check_evidence(rel)["ok"] is False
    assert V.check_file(rel, "0" * 64)["ok"] is False


def test_incomplete_escalates_to_human_after_repeats(tmp_path):
    st = tmp_path / "s.json"
    acts = [V.loop_guard({"verdict": "INCOMPLETE"}, [], st) for _ in range(3)]
    assert acts == ["VERIFY_MORE", "VERIFY_MORE", "PING_HUMAN"]


def test_reasoning_truncation_is_reported_not_passed(monkeypatch):
    c = V.NemotronClient("k", model="m")
    monkeypatch.setattr(c, "_req", lambda *a, **k: {"choices": [{"finish_reason": "length",
                                                                   "message": {"content": None}}]})
    with pytest.raises(ValueError, match="max_tokens"):
        c.chat_json("s", "u")
    claims = V.extract_claims("note", c)
    assert claims.extraction_error and "max_tokens" in claims.extraction_error
