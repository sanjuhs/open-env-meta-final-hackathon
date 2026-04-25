from __future__ import annotations

import json
import os
import urllib.request


BASE_URL = os.getenv("OPENENV_BASE_URL", "http://localhost:8000").rstrip("/")


def post(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    print("[START] mechforge_3d baseline")
    obs = post("/reset", {"task_brief": "Design a lightweight 6061 aluminum cantilever bracket with 120 N downward load at the tip."})
    print("[STEP]", json.dumps({"reset_reward": obs.get("reward"), "done": obs.get("done")}))

    actions = [
        {"tool": "create_design_family", "params": {"family": "ribbed_cantilever_bracket"}},
        {"tool": "set_material", "params": {"material": "aluminum_6061"}},
        {"tool": "set_envelope", "params": {"length_mm": 105, "width_mm": 44, "thickness_mm": 4}},
        {"tool": "add_rib", "params": {"id": "r1", "start": [16, -14, 4], "end": [88, -4, 18], "width_mm": 5, "height_mm": 18}},
        {"tool": "add_rib", "params": {"id": "r2", "start": [16, 14, 4], "end": [88, 4, 18], "width_mm": 5, "height_mm": 18}},
        {"tool": "set_load", "params": {"point_mm": [90, 0, 4], "vector_n": [0, 0, -120]}},
        {"tool": "run_fea", "params": {}},
        {"tool": "commit_design", "params": {}},
    ]

    final = None
    for index, action in enumerate(actions, start=1):
        result = post("/step", {"action": action})
        final = result
        observation = result.get("observation", {})
        metrics = observation.get("metrics", {})
        print(
            "[STEP]",
            json.dumps(
                {
                    "i": index,
                    "tool": action["tool"],
                    "reward": result.get("reward"),
                    "done": result.get("done"),
                    "score": metrics.get("score"),
                    "safety_factor": metrics.get("safety_factor"),
                    "mass_g": metrics.get("mass_g"),
                }
            ),
        )

    print("[END]", json.dumps({"final_reward": final.get("reward") if final else None, "done": final.get("done") if final else None}))


if __name__ == "__main__":
    main()

