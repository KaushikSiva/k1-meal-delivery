"""Done-Means-Done verifier agent (independent of the agent that made the claim).

Runs NVIDIA Nemotron on Crusoe Managed Inference (OpenAI-compatible) to read a teammate's handoff,
but never trusts the model for facts it can check itself:

  1. extract   - Nemotron turns a handoff note into structured claims (files+sha256, test commands
                 with expected counts, evidence paths, headline result claims).
  2. check     - deterministic re-verification, no model involved: recompute sha256, re-run
                 allowlisted pytest commands and parse pass/fail counts, confirm evidence exists.
  3. judge     - Nemotron sees claims + hard check results and returns PASS / FAIL / NEEDS_HUMAN /
                 INCOMPLETE (anything unverified: rejected commands, skipped tests, no checks,
                 model or extraction errors -- never PASS),
                 flagging overclaims (e.g. "deployable", "success rate", hardware) the evidence
                 does not support. Any failed hard check forces FAIL regardless of the model.
  4. loop guard- the same failure signature seen >= 3 times -> REPLAN (stop retrying blindly);
                 humans are pinged only on NEEDS_HUMAN or repeated failure.
  5. report    - append verdict + raw results to coordination/VERIFIER_LOG.md and a JSON record.

Usage:
  python3 agents/verifier.py --handoff coordination/CLAUDE_HANDOFF.md [--section -1] [--dry-run]
Env: CRUSOE_API_KEY (required unless --dry-run), CRUSOE_MODEL (default: first Nemotron model
listed by /v1/models), CRUSOE_BASE_URL (default https://api.inference.crusoecloud.com/v1).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("CRUSOE_BASE_URL", "https://api.inference.crusoecloud.com/v1")
STATE = ROOT / "coordination" / ".verifier_state.json"
LOG = ROOT / "coordination" / "VERIFIER_LOG.md"
ALLOWED_PYTHONS = {".venv/bin/python", "sim/.venv/bin/python", "python3"}
SAFE_FLAGS = {"-q", "-x", "-rf", "-rxX", "-rA", "--runxfail"}
SAFE_PLUGIN_OPTS = {"no:cacheprovider"}  # the ONLY value accepted after -p


def parse_test_command(command: str) -> list[str] | None:
    """Strictly validate a pytest command: known interpreter, `-m pytest`, repository test paths
    (under tests/, no '..'), a small set of flags, `-p no:cacheprovider` only, `-k <simple expr>`.
    Returns argv or None if anything is outside the allowlist."""
    try:
        argv = shlex.split(command.strip().strip("`"))
    except ValueError:
        return None
    if len(argv) < 4 or argv[0] not in ALLOWED_PYTHONS or argv[1:3] != ["-m", "pytest"]:
        return None
    i, paths = 3, 0
    while i < len(argv):
        a = argv[i]
        if a in SAFE_FLAGS:
            i += 1
        elif a == "-p" and i + 1 < len(argv) and argv[i + 1] in SAFE_PLUGIN_OPTS:
            i += 2
        elif a == "-k" and i + 1 < len(argv) and re.fullmatch(r"[\w ]+", argv[i + 1]):
            i += 2
        elif re.fullmatch(r"tests(/[\w.\-]+)*(::[\w\[\]\-]+)?", a) and ".." not in a:
            paths += 1; i += 1
        else:
            return None
    return argv if paths else None


def _inside(p: Path) -> bool:
    try:
        return p.resolve().is_relative_to(ROOT.resolve())
    except (OSError, ValueError):
        return False


# ----------------------------------------------------------------------------- env / model client
def _env_key(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name].strip()
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].split(" #")[0].strip().strip("\"'") or None
    return None


class NemotronClient:
    def __init__(self, key: str, model: str | None = None, base_url: str = BASE_URL, timeout: float = 120):
        self.key, self.base, self.timeout = key, base_url.rstrip("/"), timeout
        self.model = model or self._pick_nemotron()

    def _req(self, path: str, body: dict | None = None) -> dict:
        req = urllib.request.Request(self.base + path, None if body is None else json.dumps(body).encode(),
                                     {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
        try:
            return json.loads(urllib.request.urlopen(req, timeout=self.timeout).read())
        except urllib.error.HTTPError as e:  # never echo the key
            raise RuntimeError(f"Crusoe Managed Inference HTTP {e.code}: {e.read()[:300].decode(errors='replace')}")

    def _pick_nemotron(self) -> str:
        models = [m["id"] for m in self._req("/models").get("data", [])]
        nemo = [m for m in models if "nemotron" in m.lower()]
        if not nemo:
            raise RuntimeError(f"no Nemotron model in catalog: {models[:20]}")
        text_first = sorted(nemo, key=lambda m: ("omni" in m.lower(), len(m)))
        return text_first[0]

    def chat_json(self, system: str, user: str, max_tokens: int = 2000) -> dict:
        out = self._req("/chat/completions", {
            "model": self.model, "temperature": 0.0, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        text = out["choices"][0]["message"]["content"] or ""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)  # reasoning models
        m = re.search(r"\{.*\}", text, flags=re.S)
        if not m:
            raise ValueError(f"model returned no JSON object: {text[:200]}")
        return json.loads(m.group(0))


# ----------------------------------------------------------------------------- claims
@dataclass
class Claims:
    files: list[dict] = field(default_factory=list)   # {"path", "sha256"}
    tests: list[dict] = field(default_factory=list)   # {"command", "expect": {"passed": n, "failed": n, ...}}
    evidence: list[str] = field(default_factory=list)  # paths that must exist
    statements: list[str] = field(default_factory=list)  # headline result claims, verbatim
    extraction_error: str | None = None  # set if the model extraction failed (claims may be missing)


EXTRACT_SYSTEM = (
    "You extract verifiable claims from an engineering handoff note. Output ONLY a JSON object with keys: "
    "files (list of {path, sha256}), tests (list of {command, expect:{passed,failed,skipped,xfailed}} using only "
    "counts explicitly stated), evidence (list of repo paths cited as evidence), statements (list of the "
    "headline result claims, verbatim, max 8). Do not invent anything not in the note.")


def parse_hashes(note: str) -> list[dict]:
    """Deterministic fallback/complement: '<64 hex>  <path>' lines."""
    return [{"sha256": h, "path": p} for h, p in re.findall(r"\b([0-9a-f]{64})\s+(\S+)", note)]


def extract_claims(note: str, client: NemotronClient | None) -> Claims:
    c = Claims(files=parse_hashes(note))
    if client is not None:
        try:
            got = client.chat_json(EXTRACT_SYSTEM, note[:24000])
            known = {f["path"] for f in c.files}
            c.files += [f for f in got.get("files", []) if f.get("path") not in known and re.fullmatch(r"[0-9a-f]{64}", str(f.get("sha256", "")))]
            c.tests = [t for t in got.get("tests", []) if isinstance(t, dict) and t.get("command")]
            c.evidence = [str(e) for e in got.get("evidence", [])]
            c.statements = [str(s) for s in got.get("statements", [])][:8]
        except Exception as e:  # never silently drop claims: the run becomes INCOMPLETE
            c.extraction_error = str(e)[:300]
    return c


# ----------------------------------------------------------------------------- deterministic checks
def check_file(path: str, sha: str) -> dict:
    p = (ROOT / path).resolve()
    if not _inside(p) or not p.exists():
        return {"check": "sha256", "path": path, "ok": False, "detail": "missing or outside repo"}
    actual = hashlib.sha256(p.read_bytes()).hexdigest()
    return {"check": "sha256", "path": path, "ok": actual == sha, "detail": "match" if actual == sha else f"actual {actual[:16]}…"}


def parse_pytest_counts(out: str) -> dict:
    tail = out.strip().splitlines()[-1] if out.strip() else ""
    return {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed|skipped|xfailed|xpassed|errors?)", tail)}


def check_test(command: str, expect: dict, timeout: float = 900) -> dict:
    cmd = command.strip().strip("`")
    argv = parse_test_command(cmd)
    if argv is None:
        return {"check": "test", "command": cmd, "ok": None, "detail": "rejected by allowlist; NOT verified"}
    try:
        r = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"check": "test", "command": cmd, "ok": False, "detail": f"timeout after {timeout}s"}
    except (FileNotFoundError, PermissionError) as e:
        return {"check": "test", "command": cmd, "ok": False, "detail": f"could not execute: {e}"}
    got = parse_pytest_counts(r.stdout)
    want = {k: int(v) for k, v in (expect or {}).items() if isinstance(v, (int, float))}
    # pytest exit codes: 0 all passed, 1 some failed; 2-5 = interrupted/internal/usage/no tests.
    if r.returncode not in (0, 1) or not got:
        return {"check": "test", "command": cmd, "ok": False,
                "detail": f"did not produce a test result (exit {r.returncode}, parsed {got})"}
    ok = (all(got.get(k, 0) == v for k, v in want.items()) and got.get("failed", 0) == want.get("failed", 0)
          and got.get("errors", 0) + got.get("error", 0) == 0 and (r.returncode == 0 or want.get("failed", 0) > 0))
    return {"check": "test", "command": cmd, "ok": ok, "detail": f"exit {r.returncode}; got {got} expected {want}"}


def check_evidence(path: str) -> dict:
    p = (ROOT / path.strip("`")).resolve()
    ok = _inside(p) and p.exists()
    return {"check": "evidence", "path": path, "ok": ok, "detail": "exists" if ok else "missing"}


def run_checks(c: Claims, run_tests: bool = True) -> list[dict]:
    res = [check_file(f["path"], f["sha256"]) for f in c.files]
    if run_tests:
        res += [check_test(t["command"], t.get("expect", {})) for t in c.tests]
    res += [check_evidence(e) for e in c.evidence if not re.match(r"https?://", e)]
    return res


# ----------------------------------------------------------------------------- judge + loop guard
JUDGE_SYSTEM = (
    "You are an independent verifier on an engineering team. Decide if a teammate's handoff is DONE. "
    "You get their headline statements and the results of deterministic checks (hashes, test re-runs, "
    "evidence files). Rules: any failed check means FAIL. Flag overclaims: statements of hardware results, "
    "deployability, success rates or improvements that the cited evidence/labels do not support. "
    "Output ONLY JSON: {verdict: PASS|FAIL|NEEDS_HUMAN, definition_of_done: [short checkable criteria], "
    "overclaims: [..], reasons: [..]}. Use NEEDS_HUMAN only for decisions that genuinely require a person.")


def judge(c: Claims, checks: list[dict], client: NemotronClient | None, tests_skipped: bool = False) -> dict:
    """PASS only if every claim was actually verified and passed. Anything unverified -> INCOMPLETE."""
    hard_fail = [x for x in checks if x["ok"] is False]
    unverified = [x for x in checks if x["ok"] is None]
    reasons = [f"{x['check']} failed: {x.get('path') or x.get('command')} ({x['detail']})" for x in hard_fail]
    incomplete = []
    if not checks:
        incomplete.append("no checkable claims were verified")
    if unverified:
        incomplete += [f"{x['check']} not verified: {x.get('command') or x.get('path')} ({x['detail']})" for x in unverified]
    if tests_skipped and c.tests:
        incomplete.append(f"{len(c.tests)} claimed test command(s) were not re-run (--no-tests)")
    if c.extraction_error:
        incomplete.append(f"claim extraction failed: {c.extraction_error}")
    base = {"verdict": "FAIL" if hard_fail else ("INCOMPLETE" if incomplete else "PASS"),
            "definition_of_done": [], "overclaims": [], "reasons": reasons + incomplete}
    if client is None:
        if base["verdict"] == "PASS":
            base["verdict"] = "INCOMPLETE"  # statements were never judged without a model
        base["reasons"].append("deterministic checks only (no model): statements/overclaims not judged")
        return base
    try:
        v = client.chat_json(JUDGE_SYSTEM, json.dumps({"statements": c.statements, "checks": checks})[:24000])
    except Exception as e:
        base["reasons"].append(f"judge model error: {str(e)[:200]}")
        if base["verdict"] == "PASS":
            base["verdict"] = "INCOMPLETE"
        return base
    verdict = str(v.get("verdict", "FAIL")).upper()
    if hard_fail:  # the model can never overrule a failed hard check
        verdict = "FAIL"
    elif incomplete and verdict == "PASS":  # ...nor declare unverified work done
        verdict = "INCOMPLETE"
    return {"verdict": verdict if verdict in ("PASS", "FAIL", "NEEDS_HUMAN", "INCOMPLETE") else "FAIL",
            "definition_of_done": v.get("definition_of_done", []), "overclaims": v.get("overclaims", []),
            "reasons": base["reasons"] + list(v.get("reasons", []))}


def loop_guard(verdict: dict, checks: list[dict], state_path: Path = STATE, limit: int = 3) -> str:
    """Return the next action: CONTINUE | RETRY | REPLAN | PING_HUMAN."""
    sig = hashlib.sha256(json.dumps(sorted(
        f"{x['check']}:{x.get('path') or x.get('command')}" for x in checks if x["ok"] is False)).encode()).hexdigest()[:16]
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if verdict["verdict"] == "PASS":
        state.pop(sig, None); action = "CONTINUE"
    elif verdict["verdict"] == "NEEDS_HUMAN":
        action = "PING_HUMAN"
    elif verdict["verdict"] == "INCOMPLETE":
        key = "incomplete:" + sig
        state[key] = state.get(key, 0) + 1
        action = "PING_HUMAN" if state[key] >= limit else "VERIFY_MORE"
    else:
        state[sig] = state.get(sig, 0) + 1
        action = "REPLAN" if state[sig] >= limit else "RETRY"
    state_path.write_text(json.dumps(state, indent=1))
    return action


# ----------------------------------------------------------------------------- CLI
def handoff_section(path: Path, index: int) -> tuple[str, str]:
    text = path.read_text()
    parts = re.split(r"(?m)^## ", text)[1:]
    sec = parts[index]
    return sec.splitlines()[0].strip(), "## " + sec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handoff", required=True, type=Path)
    ap.add_argument("--section", type=int, default=-1)
    ap.add_argument("--dry-run", action="store_true", help="no model calls; deterministic checks only")
    ap.add_argument("--no-tests", action="store_true")
    a = ap.parse_args()
    title, note = handoff_section(ROOT / a.handoff if not a.handoff.is_absolute() else a.handoff, a.section)
    client = None
    if not a.dry_run:
        key = _env_key("CRUSOE_API_KEY")
        if not key:
            raise SystemExit("CRUSOE_API_KEY missing (put it in the ignored .env); use --dry-run for checks only")
        client = NemotronClient(key, os.environ.get("CRUSOE_MODEL"))
    claims = extract_claims(note, client)
    checks = run_checks(claims, run_tests=not a.no_tests)
    verdict = judge(claims, checks, client, tests_skipped=a.no_tests)
    action = loop_guard(verdict, checks)
    rec = {"at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "handoff": str(a.handoff),
           "section": title, "model": getattr(client, "model", None), "provider": "Crusoe Managed Inference" if client else None,
           "claims": asdict(claims), "checks": checks, "verdict": verdict, "next_action": action}
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(f"\n## {rec['at_utc']} — {verdict['verdict']} → {action} · {a.handoff} · {title[:80]}\n\n"
                 f"model: {rec['model'] or 'none (dry run)'} via {rec['provider'] or 'n/a'}\n\n"
                 f"- checks: {sum(1 for x in checks if x['ok'])} ok / {sum(1 for x in checks if x['ok'] is False)} failed / "
                 f"{sum(1 for x in checks if x['ok'] is None)} not run\n"
                 + "".join(f"- reason: {r}\n" for r in verdict["reasons"][:8])
                 + "".join(f"- overclaim: {o}\n" for o in verdict.get("overclaims", [])[:5])
                 + "".join(f"- done-criterion: {d}\n" for d in verdict.get("definition_of_done", [])[:6]))
    out = ROOT / "coordination" / "verifier_runs"
    out.mkdir(exist_ok=True)
    (out / f"{rec['at_utc'].replace(':', '')}.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps({"verdict": verdict["verdict"], "next_action": action, "model": rec["model"],
                      "checks_failed": [x for x in checks if x["ok"] is False]}, indent=1))


if __name__ == "__main__":
    main()
