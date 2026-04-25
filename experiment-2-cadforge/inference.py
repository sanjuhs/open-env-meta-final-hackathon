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
    with urllib.request.urlopen(request, timeout=240) as response:
        return json.loads(response.read().decode("utf-8"))


def four_leg_chair_code() -> str:
    return "\n".join(
        [
            "import cadquery as cq",
            "",
            "seat_w = 500",
            "seat_d = 460",
            "seat_t = 55",
            "leg_h = 420",
            "leg_t = 42",
            "back_h = 420",
            "back_t = 48",
            "rail_t = 28",
            "",
            "def make_seat():",
            "    return cq.Workplane('XY').box(seat_w, seat_d, seat_t).translate((0, 0, leg_h))",
            "",
            "def make_leg(x, y):",
            "    return cq.Workplane('XY').box(leg_t, leg_t, leg_h).translate((x, y, leg_h / 2))",
            "",
            "def make_backrest():",
            "    return cq.Workplane('XY').box(seat_w, back_t, back_h).translate((0, -seat_d / 2 + back_t / 2, leg_h + back_h / 2))",
            "",
            "def make_crossbar(y):",
            "    return cq.Workplane('XY').box(seat_w - leg_t, rail_t, rail_t).translate((0, y, 210))",
            "",
            "leg_x = seat_w / 2 - 58",
            "leg_y = seat_d / 2 - 58",
            "fixture = make_seat().union(make_backrest())",
            "for x in [-leg_x, leg_x]:",
            "    for y in [-leg_y, leg_y]:",
            "        fixture = fixture.union(make_leg(x, y))",
            "fixture = fixture.union(make_crossbar(-leg_y)).union(make_crossbar(leg_y)).clean()",
        ]
    )


def main() -> None:
    print("[START] cadforge_cadquery baseline")
    reset = post("/reset", {"task_id": "four_leg_chair_700n"})
    observation = reset.get("observation", reset)
    print("[STEP]", json.dumps({"reset_reward": reset.get("reward"), "task_id": observation.get("task_id")}))

    result = post(
        "/step",
        {
            "action": {
                "task_id": "four_leg_chair_700n",
                "reward_mode": "fast",
                "code": four_leg_chair_code(),
            }
        },
    )
    obs = result.get("observation", {})
    print(
        "[STEP]",
        json.dumps(
            {
                "reward": result.get("reward"),
                "done": result.get("done"),
                "reward_json": obs.get("reward_json", {}),
                "notes": obs.get("verifier_notes", []),
            }
        ),
    )
    print("[END]", json.dumps({"final_reward": result.get("reward"), "done": result.get("done")}))


if __name__ == "__main__":
    main()
