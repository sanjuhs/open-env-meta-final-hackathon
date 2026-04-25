from __future__ import annotations

import argparse
import json
import sys

from .models import Design, ToolAction, sample_design
from .solver3d import solve_3d_linear_elasticity
from .tools import run_actions


def read_json_stdin() -> dict:
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}


def main() -> None:
    parser = argparse.ArgumentParser(description="MechForge Python tools")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sample")
    sub.add_parser("simulate")
    sub.add_parser("run-actions")
    args = parser.parse_args()

    if args.command == "sample":
        design = sample_design()
        analysis = solve_3d_linear_elasticity(design)
        print(json.dumps({"design": design.model_dump(), "analysis": analysis}, indent=2))
        return

    payload = read_json_stdin()
    prompt = payload.get("prompt", "")

    if args.command == "simulate":
        design = Design.model_validate(payload.get("design", payload))
        print(json.dumps({"analysis": solve_3d_linear_elasticity(design, prompt)}, indent=2))
        return

    if args.command == "run-actions":
        actions = [ToolAction.model_validate(item) for item in payload.get("actions", [])]
        initial_design = Design.model_validate(payload["initial_design"]) if payload.get("initial_design") else None
        print(json.dumps(run_actions(actions, prompt, initial_design), indent=2))
        return


if __name__ == "__main__":
    main()
