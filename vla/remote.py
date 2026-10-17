"""HTTP client for a VLA inference server (local GPU box or managed inference).

POST {endpoint} JSON: {"task": str, "state": [16 floats], "image": {"shape","dtype","b64"}|null,
                      "timestamp": float}
Response JSON:       {"actions": [[5 floats], ...], "model_id": str}
Failures return None so the executive command is used (never blocks stopping/balance).
"""

from __future__ import annotations

import base64
import json
import time
import urllib.request

import numpy as np

from .adapter import VLAProposal


class RemoteVLAClient:
    def __init__(self, endpoint: str, timeout_s: float = 0.5, send_image: bool = True):
        self.endpoint, self.timeout_s, self.send_image = endpoint, timeout_s, send_image
        self.failures = 0

    def propose(self, inputs: dict) -> VLAProposal | None:
        img = inputs.get("observation.images.head")
        body = {
            "task": inputs["task"], "state": np.asarray(inputs["observation.state"]).tolist(), "timestamp": inputs["timestamp"],
            "image": None if (img is None or not self.send_image) else
            {"shape": list(img.shape), "dtype": str(img.dtype), "b64": base64.b64encode(img.tobytes()).decode()},
        }
        t0 = time.monotonic()
        try:
            req = urllib.request.Request(self.endpoint, json.dumps(body).encode(), {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout_s) as r:
                out = json.loads(r.read())
            return VLAProposal(np.asarray(out["actions"], float), inputs["timestamp"], out.get("model_id", "remote"),
                               time.monotonic() - t0)
        except Exception:
            self.failures += 1
            return None
