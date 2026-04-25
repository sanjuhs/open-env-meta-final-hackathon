from __future__ import annotations

import json
import os
import urllib.request


class CadForgeClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("OPENENV_BASE_URL", "http://localhost:8000")).rstrip("/")

    def reset(self, **payload: object) -> dict:
        return self._post("/reset", payload)

    def step(self, action: dict) -> dict:
        return self._post("/step", {"action": action})

    def _post(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=240) as response:
            return json.loads(response.read().decode("utf-8"))

