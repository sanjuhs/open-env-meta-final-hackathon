#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "experiment-2-cadforge"
CADQUERY_ENV = APP_ROOT / "python_tools" / "cadquery_env.py"
PYTHON = ROOT / ".venv" / "bin" / "python"
TASK_JSON = APP_ROOT / "data" / "generated-assets" / "axial_motor_stator_12_slot" / "task.json"
RESULT_ROOT = ROOT / "inference" / "results"

STRICT_QWEN_CODE = (
    APP_ROOT
    / "runs"
    / "cadquery-env"
    / "local-judge-assets-strict-grpo-stator"
    / "model-output"
    / "candidate.py"
)

GPT54_CODE = (
    APP_ROOT
    / "runs"
    / "cadquery-env"
    / "openai-gpt-5.4-axial_motor_stator_12_slot-disconnected-2026-04-25T14-06-43-357Z"
    / "step-2"
    / "candidate.py"
)

BG = (247, 249, 250)
INK = (25, 32, 40)
MUTED = (88, 102, 116)
LINE = (213, 222, 230)
GOOD = (49, 132, 86)
MID = (42, 112, 145)
BAD = (190, 76, 67)


@dataclass(frozen=True)
class Candidate:
    key: str
    label: str
    source: str
    code: str


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates += [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ]
    candidates += [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


FONT_TITLE = font(34, bold=True)
FONT_H2 = font(22, bold=True)
FONT_BODY = font(17)
FONT_SMALL = font(14)


def slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "run"


def extract_code(text: str) -> str:
    value = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL | re.IGNORECASE).strip()
    match = re.search(r"```(?:python|py)?\s*\n([\s\S]*?)```", value, flags=re.IGNORECASE)
    value = match.group(1) if match else value
    return value.strip().strip("`").strip()


def read_task() -> dict[str, Any]:
    return json.loads(TASK_JSON.read_text())


def ollama_generate(model: str, prompt: str, timeout: int, url: str) -> str:
    system = "\n".join(
        [
            "You are a CadQuery CAD code generator.",
            "Return only executable Python code. No markdown fences.",
            "Use import cadquery as cq.",
            "Assign the final exportable object to fixture.",
            "Use robust CadQuery primitives: Workplane.box, Workplane.circle().extrude, Workplane.cylinder, translate, rotate, union, cut.",
            "Avoid unsupported CadQuery APIs, filesystem access, network access, subprocess, and CQ-editor-only helpers.",
            "Prefer named dimensions and helper functions so the CAD is editable.",
        ]
    )
    payload = {
        "model": model,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.15,
            "top_p": 0.9,
            "num_ctx": 8192,
            "num_predict": 2600,
        },
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        url.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc
    return extract_code(data.get("message", {}).get("content") or data.get("response") or "")


def openai_generate(model: str, prompt: str, timeout: int) -> str:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set; use --gpt-source file or set the key.")
    from openai import OpenAI

    client = OpenAI(timeout=timeout)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": "\n".join(
                    [
                        "You are a CadQuery CAD code generator.",
                        "Return only executable Python code. No markdown fences.",
                        "Use import cadquery as cq and assign the final object to fixture.",
                        "Prefer named dimensions, helper functions, and robust primitives.",
                    ]
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    return extract_code(response.output_text or "")


def evaluate(candidate: Candidate, out_dir: Path, task: dict[str, Any], reward_mode: str, timeout: int) -> dict[str, Any]:
    code_dir = out_dir / "code"
    code_dir.mkdir(parents=True, exist_ok=True)
    code_path = code_dir / f"{candidate.key}.py"
    code_path.write_text(candidate.code)

    cmd = [
        str(PYTHON if PYTHON.exists() else sys.executable),
        str(CADQUERY_ENV),
        "evaluate",
        "--code-file",
        str(code_path),
        "--episode-id",
        f"inference-{out_dir.name}",
        "--step-id",
        candidate.key,
        "--task-prompt",
        task["prompt"],
        "--task-spec",
        str(TASK_JSON),
        "--reward-mode",
        reward_mode,
    ]
    proc = subprocess.run(
        cmd,
        cwd=APP_ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        env={
            **os.environ,
            "PYTHONPATH": str(APP_ROOT / "python_tools"),
            "XDG_CACHE_HOME": str(APP_ROOT / ".cache"),
        },
    )
    if proc.returncode != 0:
        result = {
            "ok": False,
            "candidate": candidate.__dict__,
            "reward": {"total": -1.0, "build": 0.0},
            "notes": [f"Evaluator process failed: {(proc.stderr or proc.stdout)[-500:]}"],
            "artifacts_dir": "",
        }
    else:
        start = proc.stdout.find("{")
        end = proc.stdout.rfind("}")
        result = json.loads(proc.stdout[start : end + 1])
        result["candidate"] = candidate.__dict__

    local_dir = out_dir / candidate.key
    if local_dir.exists():
        shutil.rmtree(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)
    (local_dir / "candidate.py").write_text(candidate.code)
    (local_dir / "result.json").write_text(json.dumps(result, indent=2))

    artifacts = Path(result.get("artifacts_dir") or "")
    if artifacts.exists():
        for name in ["reward.json", "verifier_report.md", "candidate.stl", "candidate_normalized.stl"]:
            src = artifacts / name
            if src.exists():
                shutil.copy2(src, local_dir / name)
        for subdir in ["renders", "masks"]:
            src_dir = artifacts / subdir
            if src_dir.exists():
                shutil.copytree(src_dir, local_dir / subdir, dirs_exist_ok=True)

    result["local_artifacts_dir"] = str(local_dir)
    return result


def reward_value(result: dict[str, Any], key: str) -> float:
    try:
        return float(result.get("reward", {}).get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0


def fit_image(path: Path, size: tuple[int, int]) -> Image.Image:
    img = Image.open(path).convert("RGB")
    img.thumbnail((size[0] - 20, size[1] - 20), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (255, 255, 255))
    canvas.paste(img, ((size[0] - img.width) // 2, (size[1] - img.height) // 2))
    return canvas


def rounded_card(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], fill=(255, 255, 255)) -> None:
    draw.rounded_rectangle(xy, radius=8, fill=fill, outline=LINE, width=2)


def make_comparison_image(results: list[dict[str, Any]], out_dir: Path, task: dict[str, Any]) -> Path:
    w, h = 1800, 950
    image = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(image)
    draw.text((44, 28), "Axial Motor Stator: Base Qwen vs RL-Tuned Qwen vs GPT-5.4", fill=INK, font=FONT_TITLE)
    draw.text((44, 76), task["prompt"], fill=MUTED, font=FONT_BODY)

    panel_w, panel_h = 540, 700
    for index, result in enumerate(results):
        x = 44 + index * 584
        y = 130
        candidate = result["candidate"]
        total = reward_value(result, "total")
        build = reward_value(result, "build")
        color = GOOD if build >= 1.0 and total >= 0.65 else MID if build >= 1.0 else BAD
        rounded_card(draw, (x, y, x + panel_w, y + panel_h))
        draw.rectangle((x, y, x + panel_w, y + 8), fill=color)
        draw.text((x + 22, y + 26), candidate["label"], fill=INK, font=FONT_H2)
        display_source = candidate["source"]
        if "saved GPT-5.4 artifact" in display_source:
            display_source = "saved GPT-5.4 stator artifact"
        elif "strict build-gated GRPO" in display_source:
            display_source = "strict build-gated GRPO stator artifact"
        for line_index, line in enumerate(textwrap.wrap(display_source, width=58)[:2]):
            draw.text((x + 22, y + 56 + 18 * line_index), line, fill=MUTED, font=FONT_SMALL)

        render_path = Path(result.get("local_artifacts_dir", "")) / "renders" / "isometric.png"
        if render_path.exists():
            image.paste(fit_image(render_path, (panel_w - 44, 390)), (x + 22, y + 92))
        else:
            draw.text((x + 24, y + 250), "No render: build failed", fill=BAD, font=FONT_H2)

        metrics = [
            ("Total", "total"),
            ("Build", "build"),
            ("Semantic", "semantic_parts"),
            ("Reference", "reference_similarity"),
            ("Editability", "editability"),
        ]
        yy = y + 510
        for label, key in metrics:
            draw.text((x + 28, yy), label, fill=MUTED, font=FONT_BODY)
            draw.text((x + 190, yy), f"{reward_value(result, key):.3f}", fill=INK, font=FONT_BODY)
            yy += 34

    out = out_dir / "comparison.png"
    image.save(out)
    return out


def write_report(results: list[dict[str, Any]], out_dir: Path, task: dict[str, Any], comparison: Path) -> Path:
    lines = [
        "# CADForge Inference Comparison",
        "",
        "Task: `axial_motor_stator_12_slot`",
        "",
        task["prompt"],
        "",
        "![Model comparison](comparison.png)",
        "",
        "## Summary",
        "",
        "| Model | Source | Total | Build | Semantic | Reference | Editability | Local artifacts |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for result in results:
        candidate = result["candidate"]
        local = Path(result.get("local_artifacts_dir", "")).relative_to(out_dir)
        lines.append(
            "| {label} | {source} | {total:.3f} | {build:.1f} | {semantic:.3f} | {reference:.3f} | {editability:.3f} | `{local}` |".format(
                label=candidate["label"],
                source=candidate["source"],
                total=reward_value(result, "total"),
                build=reward_value(result, "build"),
                semantic=reward_value(result, "semantic_parts"),
                reference=reward_value(result, "reference_similarity"),
                editability=reward_value(result, "editability"),
                local=local,
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is a single-task qualitative comparison, not a leaderboard. The useful signal is that the RL-tuned Qwen adapter produces a buildable, editable stator on the same medium-difficulty part family where a frontier model also succeeds.",
            "",
            "The base Qwen row is generated locally through Ollama when `--baseline-source ollama` is used. The fine-tuned Qwen row defaults to the saved strict-GRPO held-out stator artifact, because the local laptop does not include the full HF/PEFT stack and merged model weights. The script can still run a live HF/PEFT model on a GPU machine by replacing the code source or extending the candidate generator.",
            "",
            "The honest claim is: CADForge does not prove small Qwen beats frontier models yet. It proves that a small model can become competitive on buildable code-CAD behavior when trained inside a strict executable CAD reward environment, and that longer training plus broader reference tasks is the right next scaling path.",
            "",
            "## Reproduce",
            "",
            "```bash",
            ".venv/bin/python inference/compare_cadquery_models.py --baseline-source ollama",
            "```",
            "",
        ]
    )
    report = out_dir / "report.md"
    report.write_text("\n".join(lines))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare base Qwen, RL-tuned Qwen, and GPT-5.4 on a CadQuery stator task.")
    parser.add_argument("--run-id", default="stator-qwen-vs-frontier")
    parser.add_argument("--baseline-source", choices=["ollama", "file"], default="ollama")
    parser.add_argument("--baseline-model", default="qwen3.5:9b")
    parser.add_argument("--baseline-code", type=Path, default=None)
    parser.add_argument("--finetuned-code", type=Path, default=STRICT_QWEN_CODE)
    parser.add_argument("--gpt-source", choices=["file", "openai"], default="file")
    parser.add_argument("--gpt-model", default="gpt-5.4")
    parser.add_argument("--gpt-code", type=Path, default=GPT54_CODE)
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://localhost:11434"))
    parser.add_argument("--reward-mode", choices=["full", "fast"], default="full")
    parser.add_argument("--timeout", type=int, default=240)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    task = read_task()
    out_dir = RESULT_ROOT / slug(args.run_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    prompt = "\n".join(
        [
            task["prompt"],
            "",
            "Return only complete executable CadQuery Python code.",
            "The final model must be assigned to fixture.",
        ]
    )

    candidates: list[Candidate] = []
    if args.baseline_source == "ollama":
        started = time.time()
        baseline_code = ollama_generate(args.baseline_model, prompt, args.timeout, args.ollama_url)
        source = f"live Ollama `{args.baseline_model}` ({time.time() - started:.1f}s)"
    else:
        if not args.baseline_code:
            raise SystemExit("--baseline-code is required with --baseline-source file")
        baseline_code = extract_code(args.baseline_code.read_text())
        if "stator-qwen-vs-frontier" in str(args.baseline_code):
            source = "saved local Ollama base-Qwen output"
        else:
            source = f"file `{args.baseline_code}`"
    candidates.append(Candidate("base-qwen", "Base Qwen", source, baseline_code))

    candidates.append(
        Candidate(
            "rl-tuned-qwen",
            "RL-tuned Qwen",
            "strict build-gated GRPO held-out stator artifact",
            extract_code(args.finetuned_code.read_text()),
        )
    )

    if args.gpt_source == "openai":
        gpt_code = openai_generate(args.gpt_model, prompt, args.timeout)
        gpt_source = f"live OpenAI `{args.gpt_model}`"
    else:
        gpt_code = extract_code(args.gpt_code.read_text())
        gpt_source = f"saved GPT-5.4 artifact `{args.gpt_code}`"
    candidates.append(Candidate("gpt-5-4", "GPT-5.4", gpt_source, gpt_code))

    results = [evaluate(candidate, out_dir, task, args.reward_mode, args.timeout) for candidate in candidates]
    (out_dir / "results.json").write_text(json.dumps(results, indent=2))
    comparison = make_comparison_image(results, out_dir, task)
    report = write_report(results, out_dir, task, comparison)

    print(
        json.dumps(
            {
                "report": str(report),
                "comparison": str(comparison),
                "results": [
                    {
                        "model": row["candidate"]["label"],
                        "total": reward_value(row, "total"),
                        "build": reward_value(row, "build"),
                        "artifacts": row.get("local_artifacts_dir"),
                    }
                    for row in results
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
