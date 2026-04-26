#!/usr/bin/env python3
"""Build an adaptive CADForge repair curriculum from GRPO failure traces."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SYSTEM_PROMPT = """You are CADForge, a careful CadQuery CAD repair agent.
Return only a complete executable Python CadQuery file. Do not return markdown fences.
Use import cadquery as cq.
Assign the final exportable object to fixture.
Prefer named dimensions and helper functions so the CAD can be edited in later steps.
Use conservative CadQuery operations: box, cylinder, circle/extrude, union, cut, fillet, translate, rotate.
Do not invent APIs like Workplane.cone, Workplane.annulus, or helper methods that are not defined.
End with a valid fixture assignment, usually fixture = fixture.clean()."""


POLICIES = {
    "syntax_closure": [
        "Produce a shorter valid file instead of continuing the broken long program.",
        "Close all parentheses, lists, chained unions, and function bodies.",
        "Avoid trailing partial expressions; end with fixture = fixture.clean().",
    ],
    "missing_fixture": [
        "Create all parts, combine them, and assign the final object to fixture.",
        "Do not leave the model in a variable named assembly, result, or model unless fixture also points to it.",
    ],
    "invented_api": [
        "Replace unsupported CadQuery helpers with boxes, cylinders, circle/extrude, cuts, unions, translate, and rotate.",
        "If a shape is hard, approximate it with conservative primitives that compile.",
    ],
    "undefined_name": [
        "Define every dimension, helper, and intermediate before it is used.",
        "Use explicit named dimensions and avoid references to variables from previous attempts.",
    ],
    "type_or_value": [
        "Simplify the failing operation and avoid fragile selectors, lofts, sweeps, and ambiguous boolean operations.",
        "Use reliable primitive unions and cuts with small overlaps.",
    ],
    "disconnected_or_weak": [
        "Add bridges, overlaps, ribs, crossbars, bosses, or root blocks so major parts are physically connected.",
        "Improve task semantics with recognizable requested parts while keeping one final fixture.",
    ],
    "low_editability": [
        "Add named dimensions and helper functions for repeated subassemblies.",
        "Keep the final file compact, reusable, and parameterized.",
    ],
    "unknown_build_failure": [
        "Rewrite the candidate into a simpler buildable CadQuery version.",
        "Preserve the task intent, but prioritize executable CAD first.",
    ],
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(errors="ignore") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_tasks(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return {str(row.get("id")): row for row in data if row.get("id")}
    if isinstance(data, dict):
        return {str(key): value for key, value in data.items() if isinstance(value, dict)}
    return {}


def reward_dict(row: dict[str, Any]) -> dict[str, Any]:
    reward = row.get("cadforge_reward")
    if isinstance(reward, dict):
        return reward
    tail = str(row.get("cadforge_stdout_tail") or "")
    start = tail.find("{")
    end = tail.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(tail[start : end + 1])
        except json.JSONDecodeError:
            return {}
        maybe = parsed.get("reward")
        if isinstance(maybe, dict):
            return maybe
    return {}


def combined_error_text(row: dict[str, Any]) -> str:
    return "\n".join(
        str(row.get(key) or "")
        for key in ["cadforge_error", "cadforge_stdout_tail", "cadforge_stderr_tail", "completion_head", "code_head"]
    )


def classify_failure(row: dict[str, Any]) -> str:
    reward = reward_dict(row)
    code = str(row.get("code") or row.get("code_head") or "")
    text = combined_error_text(row)
    if float(row.get("cadforge_build", reward.get("build", 0.0)) or 0.0) >= 1.0:
        if float(reward.get("editability", 0.0) or 0.0) < 0.65:
            return "low_editability"
        if float(reward.get("semantic_parts", 0.0) or 0.0) < 0.45:
            return "disconnected_or_weak"
        return "build_ok"
    if "SyntaxError" in text or code.count("(") != code.count(")") or code.count("[") != code.count("]"):
        return "syntax_closure"
    if not re.search(r"\bfixture\s*=", code):
        return "missing_fixture"
    if any(token in text for token in ["AttributeError", "Workplane' object has no attribute", ".annulus", ".cone", ".sphere"]):
        return "invented_api"
    if "NameError" in text:
        return "undefined_name"
    if any(token in text for token in ["TypeError", "ValueError", "StdFail", "BRep_API", "Null TopoDS"]):
        return "type_or_value"
    return "unknown_build_failure"


def compact_reward(row: dict[str, Any]) -> dict[str, float]:
    reward = reward_dict(row)
    keys = ["total", "build", "topology", "contact", "semantic_parts", "reference_similarity", "editability"]
    out: dict[str, float] = {}
    for key in keys:
        try:
            out[key] = round(float(reward.get(key, row.get(f"cadforge_{key}", 0.0)) or 0.0), 4)
        except (TypeError, ValueError):
            out[key] = 0.0
    if not out["total"]:
        try:
            out["total"] = round(float(row.get("cadforge_total", row.get("score", 0.0)) or 0.0), 4)
        except (TypeError, ValueError):
            out["total"] = 0.0
    return out


def failure_observation(row: dict[str, Any], failure_type: str) -> str:
    reward = compact_reward(row)
    error_text = combined_error_text(row)
    error_lines = [line.strip() for line in error_text.splitlines() if line.strip()]
    tail = "\n".join(error_lines[-12:])
    return json.dumps(
        {
            "failure_type": failure_type,
            "previous_reward": reward,
            "error_tail": tail[-1800:],
        },
        indent=2,
    )


def make_messages(row: dict[str, Any], task: dict[str, Any], failure_type: str, curriculum_weight: float) -> list[dict[str, str]]:
    code = str(row.get("code") or row.get("code_head") or "").strip()
    policy = "\n".join(f"- {item}" for item in POLICIES.get(failure_type, POLICIES["unknown_build_failure"]))
    hints = task.get("semantic_hints") if isinstance(task.get("semantic_hints"), list) else []
    prompt = task.get("prompt") or str(row.get("task_prompt") or "")
    user = f"""Task:
{prompt}

Semantic hints:
{", ".join(map(str, hints)) if hints else "Use the task prompt."}

Previous candidate failed CADForge verification.

Observation:
{failure_observation(row, failure_type)}

Adaptive repair policy for this failure:
{policy}

Curriculum weight: {curriculum_weight:.3f}

Previous CadQuery code:
{code[:12000]}

Repair it into a complete executable CadQuery Python file. Return only the repaired Python file."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debug-jsonl", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, default=Path("experiment-2-cadforge/data/cad_tasks.json"))
    parser.add_argument("--output", type=Path, default=Path("training/output/cadforge_adaptive_repair_curriculum.jsonl"))
    parser.add_argument("--summary", type=Path, default=Path("training/output/cadforge_adaptive_repair_summary.json"))
    parser.add_argument("--max-rows", type=int, default=180)
    parser.add_argument("--include-buildable-weak", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.debug_jsonl)
    tasks = load_tasks(args.tasks)

    task_counts: Counter[str] = Counter()
    task_builds: Counter[str] = Counter()
    failure_counts: Counter[str] = Counter()
    candidates: list[dict[str, Any]] = []
    for row in rows:
        task_id = str(row.get("task_id") or "")
        reward = reward_dict(row)
        build = float(row.get("cadforge_build", reward.get("build", 0.0)) or 0.0)
        task_counts[task_id] += 1
        if build >= 1.0:
            task_builds[task_id] += 1
        failure_type = classify_failure(row)
        if failure_type == "build_ok" and not args.include_buildable_weak:
            continue
        failure_counts[failure_type] += 1
        candidates.append({"row": row, "failure_type": failure_type})

    failure_rank = {name: rank for rank, (name, _) in enumerate(failure_counts.most_common(), start=1)}
    output_rows: list[dict[str, Any]] = []
    for item in candidates:
        row = item["row"]
        failure_type = item["failure_type"]
        task_id = str(row.get("task_id") or "")
        task = tasks.get(task_id, {"id": task_id, "prompt": row.get("task_prompt", "")})
        total = max(1, task_counts[task_id])
        build_rate = task_builds[task_id] / total
        failure_boost = 1.0 + 0.20 * max(0, len(failure_rank) - failure_rank.get(failure_type, len(failure_rank)))
        curriculum_weight = round((1.0 + (1.0 - build_rate) ** 2) * failure_boost, 4)
        score = float(row.get("score", row.get("cadforge_total", 0.0)) or 0.0)
        output_rows.append(
            {
                "messages": make_messages(row, task, failure_type, curriculum_weight),
                "task_id": task_id,
                "task_spec": task,
                "dataset_type": "adaptive_repair_grpo_prompt",
                "failure_type": failure_type,
                "curriculum_weight": curriculum_weight,
                "previous_score": score,
                "previous_reward": compact_reward(row),
                "source_reward_call": row.get("reward_call"),
                "source_index": row.get("index"),
            }
        )

    output_rows.sort(key=lambda row: (-float(row["curriculum_weight"]), row["failure_type"], row["task_id"]))
    output_rows = output_rows[: args.max_rows]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as handle:
        for row in output_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "source_rows": len(rows),
        "output_rows": len(output_rows),
        "failure_counts": dict(failure_counts),
        "task_counts": dict(task_counts),
        "task_builds": dict(task_builds),
        "output": str(args.output),
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
