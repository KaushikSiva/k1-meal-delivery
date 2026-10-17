#!/usr/bin/env python3
"""Local deadline guard: stop ONE authorized Brev instance, then verify its state.

Uses native Brev authentication; never reads or prints credentials. This process
must remain running on a connected host. It cannot guarantee a provider billing
cap during host sleep/network outage; retries continue after connectivity returns.
This is a cost-control timer, not an agent progress heartbeat.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time


def find_instance(payload, name):
    matches = [w for w in payload.get("workspaces") or [] if w.get("name") == name]
    if len(matches) > 1:
        raise ValueError("Instance name is ambiguous; refusing to stop multiple machines")
    return matches[0] if matches else None


def run(cli, name, deadline, state_file):
    if not name or name.startswith("-") or not all(c.isalnum() or c == "-" for c in name):
        raise ValueError("Expected one explicit instance name")
    parsed_deadline = datetime.fromisoformat(deadline)
    if parsed_deadline.tzinfo is None:
        raise ValueError("Deadline must include a timezone offset")
    deadline_epoch = parsed_deadline.timestamp()
    state_file.parent.mkdir(parents=True, exist_ok=True)

    def record(state, **extra):
        payload = {"instance": name, "deadline_utc": deadline, "state": state,
                   "updated_at_utc": datetime.now(timezone.utc).isoformat(), **extra}
        temp = state_file.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2) + "\n")
        temp.replace(state_file)
        print(json.dumps(payload), flush=True)

    record("armed")
    while time.time() < deadline_epoch:
        time.sleep(max(0, min(30, deadline_epoch - time.time())))
    while True:
        try:
            result = subprocess.run([cli, "ls", "--all", "--json"], capture_output=True,
                                    text=True, timeout=45, check=True)
            instance = find_instance(json.loads(result.stdout), name)
            if instance is None:
                record("instance_absent")
                return
            status = str(instance.get("status", "unknown")).lower()
            if status in {"stopped", "deleted", "terminated"}:
                record("verified_stopped", provider_status=status)
                return
            result = subprocess.run([cli, "stop", name], capture_output=True, text=True, timeout=60)
            record("stop_requested", returncode=result.returncode, previous_status=status)
        except (subprocess.SubprocessError, ValueError, OSError) as exc:
            # Exception messages may contain command details; record class only.
            record("retry_required", error_type=type(exc).__name__)
        time.sleep(30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--deadline", required=True, help="ISO timestamp with UTC offset")
    parser.add_argument("--state-file", required=True, type=Path)
    args = parser.parse_args()
    run(args.cli, args.instance, args.deadline, args.state_file)
