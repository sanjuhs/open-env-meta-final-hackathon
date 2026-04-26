#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "matplotlib",
#     "numpy",
#     "tensorboard",
# ]
# ///
"""Parse CADForge training logs/events and generate charts plus Markdown."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any


def parse_metrics(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    text = log_path.read_text(errors="ignore").replace("\r", "\n")
    rows: list[dict[str, Any]] = []
    for match in re.finditer(r"\{[^{}\n]*(?:loss|eval_loss|train_runtime|reward|grad_norm|learning_rate)[^{}\n]*\}", text):
        try:
            item = ast.literal_eval(match.group(0))
        except (SyntaxError, ValueError):
            continue
        if not isinstance(item, dict):
            continue
        parsed: dict[str, Any] = {}
        for key, value in item.items():
            try:
                parsed[key] = float(value)
            except (TypeError, ValueError):
                parsed[key] = value
        rows.append(parsed)
    return rows


def load_tensorboard_scalars(path: Path | None) -> dict[str, list[dict[str, float]]]:
    if path is None or not path.exists():
        return {}
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

    event_files = [path] if path.is_file() else sorted(path.rglob("events.out.tfevents.*"))
    scalars: dict[str, list[dict[str, float]]] = {}
    for event_dir in sorted({event.parent for event in event_files}):
        try:
            accumulator = EventAccumulator(str(event_dir), size_guidance={"scalars": 0})
            accumulator.Reload()
        except Exception:
            continue
        for tag in accumulator.Tags().get("scalars", []):
            for event in accumulator.Scalars(tag):
                scalars.setdefault(tag, []).append({
                    "step": float(event.step),
                    "value": float(event.value),
                    "wall_time": float(event.wall_time),
                })
    for tag in scalars:
        scalars[tag].sort(key=lambda row: (row["step"], row["wall_time"]))
    return scalars


def error_kind(row: dict[str, Any], notes: list[Any]) -> str:
    text = "\n".join(str(note) for note in notes)
    text += "\n" + str(row.get("cadforge_stdout_tail") or "")
    for key in ["SyntaxError", "AttributeError", "TypeError", "ValueError", "NameError", "BRep_API", "StdFail"]:
        if key in text:
            return key
    if float(row.get("cadforge_build", 0.0) or 0.0) > 0:
        return "build_ok"
    if float(row.get("score", 0.0) or 0.0) > 0:
        return "shaped_build_fail"
    return "unknown"


def parse_debug_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        reward_json: dict[str, Any] = {}
        tail = str(row.get("cadforge_stdout_tail") or "").strip()
        if tail.startswith("{"):
            try:
                reward_json = json.loads(tail)
            except json.JSONDecodeError:
                reward_json = {}
        reward = reward_json.get("reward") if isinstance(reward_json.get("reward"), dict) else {}
        row["cadforge_ok"] = bool(reward_json.get("ok")) if reward_json else False
        if "cadforge_build" not in row:
            row["cadforge_build"] = float(reward.get("build", 0.0) or 0.0)
        if "cadforge_total" not in row:
            row["cadforge_total"] = float(reward.get("total", row.get("score", 0.0)) or 0.0)
        notes = reward_json.get("notes") if isinstance(reward_json.get("notes"), list) else []
        row["cadforge_notes"] = notes
        row["error_kind"] = error_kind(row, notes)
        rows.append(row)
    return rows


def split_series(rows: list[dict[str, Any]]) -> tuple[list[tuple[int, float]], list[tuple[int, float]], dict[str, Any]]:
    train: list[tuple[int, float]] = []
    evals: list[tuple[int, float]] = []
    final: dict[str, Any] = {}
    train_step = 0
    for row in rows:
        if "loss" in row:
            train_step += 1
            train.append((train_step, float(row["loss"])))
        if "eval_loss" in row:
            evals.append((train_step, float(row["eval_loss"])))
        if "train_runtime" in row:
            final = row
    return train, evals, final


def scalar_points(
    scalars: dict[str, list[dict[str, float]]],
    *needles: str,
    exclude: tuple[str, ...] = (),
) -> list[tuple[float, float, float]]:
    for tag in sorted(scalars):
        low = tag.lower()
        if all(needle.lower() in low for needle in needles) and not any(item.lower() in low for item in exclude):
            return [(row["step"], row["value"], row["wall_time"]) for row in scalars[tag]]
    return []


def rolling(values: list[float], window: int = 10) -> list[float]:
    out: list[float] = []
    for index in range(len(values)):
        chunk = values[max(0, index - window + 1) : index + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def slope(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(ys) < 2:
        return None
    import numpy as np

    try:
        return float(np.polyfit(xs, ys, 1)[0])
    except Exception:
        return None


def plot_loss_curves(
    train: list[tuple[int, float]],
    evals: list[tuple[int, float]],
    scalars: dict[str, list[dict[str, float]]],
    output_png: Path,
) -> None:
    import matplotlib.pyplot as plt

    tb_train = scalar_points(scalars, "loss", exclude=("eval", "grad", "reward"))
    tb_eval = scalar_points(scalars, "eval", "loss")
    if tb_train:
        train = [(int(step), value) for step, value, _ in tb_train]
    if tb_eval:
        evals = [(int(step), value) for step, value, _ in tb_eval]

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5), dpi=160)
    if train:
        xs = [x for x, _ in train]
        ys = [y for _, y in train]
        ax.plot(xs, ys, label="train loss", linewidth=1.1, alpha=0.55)
        ax.plot(xs, rolling(ys, 10), label="train rolling avg (10)", linewidth=2.4)
    if evals:
        ax.plot([x for x, _ in evals], [y for _, y in evals], label="eval loss", marker="o", linewidth=2.0)
    ax.set_title("CADForge Qwen SFT Loss")
    ax.set_xlabel("optimizer step")
    ax.set_ylabel("loss")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_png)
    plt.close(fig)


def plot_scalar_pair(
    scalars: dict[str, list[dict[str, float]]],
    output_png: Path,
    title: str,
    series: list[tuple[str, tuple[str, ...], tuple[str, ...]]],
) -> list[str]:
    import matplotlib.pyplot as plt

    plotted: list[str] = []
    fig, ax = plt.subplots(figsize=(9, 5), dpi=160)
    for label, needles, exclude in series:
        points = scalar_points(scalars, *needles, exclude=exclude)
        if not points:
            continue
        ax.plot([step for step, _, _ in points], [value for _, value, _ in points], label=label, linewidth=2.0)
        plotted.append(label)
    ax.set_title(title)
    ax.set_xlabel("optimizer step")
    ax.grid(True, alpha=0.25)
    if plotted:
        ax.legend()
    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png)
    plt.close(fig)
    return plotted


def plot_timeline(scalars: dict[str, list[dict[str, float]]], output_png: Path, title: str) -> bool:
    import matplotlib.pyplot as plt

    candidates = [
        ("reward", scalar_points(scalars, "reward", "mean", exclude=("std",))),
        ("loss", scalar_points(scalars, "loss", exclude=("eval", "grad", "reward"))),
        ("grad norm", scalar_points(scalars, "grad_norm")),
    ]
    candidates = [(label, points) for label, points in candidates if points]
    if not candidates:
        return False
    all_times = [wall_time for _, points in candidates for _, _, wall_time in points]
    start = min(all_times)
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=160)
    for label, points in candidates:
        steps = [step for step, _, _ in points]
        minutes = [(wall_time - start) / 60.0 for _, _, wall_time in points]
        ax.plot(steps, minutes, label=label, linewidth=2.0)
    ax.set_title(title)
    ax.set_xlabel("optimizer step")
    ax.set_ylabel("elapsed minutes since first event")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png)
    plt.close(fig)
    return True


def plot_reward_curve(
    scalars: dict[str, list[dict[str, float]]],
    debug_rows: list[dict[str, Any]],
    output_png: Path,
    title: str,
) -> dict[str, Any]:
    import matplotlib.pyplot as plt
    import numpy as np

    points = scalar_points(scalars, "reward", "mean", exclude=("std",))
    if not points:
        points = scalar_points(scalars, "reward", exclude=("std",))
    if points:
        xs = [step for step, _, _ in points]
        ys = [value for _, value, _ in points]
    else:
        grouped: dict[int, list[float]] = {}
        for row in debug_rows:
            grouped.setdefault(int(row.get("reward_call", 0) or 0), []).append(float(row.get("score", 0.0) or 0.0))
        xs = sorted(key for key in grouped if key)
        ys = [sum(grouped[key]) / len(grouped[key]) for key in xs]

    summary: dict[str, Any] = {"points": len(xs)}
    if ys:
        trend = slope([float(x) for x in xs], ys)
        summary.update({"first": ys[0], "last": ys[-1], "best": max(ys), "mean": sum(ys) / len(ys), "slope": trend})

    fig, ax = plt.subplots(figsize=(10, 5.4), dpi=160)
    if xs and ys:
        ax.plot(xs, ys, color="#9aa0ff", marker="o", linewidth=1.5, alpha=0.75, label="per step")
        ax.plot(xs, rolling(ys, 10), color="#0b23ff", linewidth=2.7, label="rolling avg (10)")
        trend = summary.get("slope")
        if trend is not None and len(xs) > 1:
            intercept = float(np.mean(ys) - trend * np.mean(xs))
            trend_line = [trend * x + intercept for x in xs]
            direction = "up" if trend >= 0 else "down"
            ax.plot(xs, trend_line, color="red", linestyle="--", linewidth=1.6, label=f"trend ({direction} {trend:.4f}/step)")
        ax.axhline(0.0, color="#888888", linestyle="--", linewidth=1.0, alpha=0.55)
        box = f"Steps: {len(xs)} | Mean: {summary['mean']:.3f} | Best: {summary['best']:.3f}"
        ax.text(0.02, 0.04, box, transform=ax.transAxes, fontsize=9, bbox={"boxstyle": "round", "facecolor": "#fff7e6", "alpha": 0.85})
    ax.set_title(title)
    ax.set_xlabel("GRPO optimizer step")
    ax.set_ylabel("reward")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png)
    plt.close(fig)
    return summary


def plot_debug_health(debug_rows: list[dict[str, Any]], output_png: Path) -> dict[str, Any]:
    import matplotlib.pyplot as plt

    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in debug_rows:
        grouped.setdefault(int(row.get("reward_call", 0) or 0), []).append(row)
    xs = sorted(key for key in grouped if key)
    build_rate: list[float] = []
    fixture_rate: list[float] = []
    import_rate: list[float] = []
    avg_chars: list[float] = []
    for key in xs:
        chunk = grouped[key]
        build_rate.append(sum(1 for row in chunk if float(row.get("cadforge_build", 0.0) or 0.0) > 0) / len(chunk))
        fixture_rate.append(sum(1 for row in chunk if row.get("has_fixture")) / len(chunk))
        import_rate.append(sum(1 for row in chunk if row.get("has_cadquery_import")) / len(chunk))
        avg_chars.append(sum(float(row.get("code_chars", 0.0) or 0.0) for row in chunk) / len(chunk))

    summary = {
        "debug_rows": len(debug_rows),
        "reward_calls": len(xs),
        "overall_build_rate": sum(1 for row in debug_rows if float(row.get("cadforge_build", 0.0) or 0.0) > 0) / len(debug_rows) if debug_rows else 0.0,
        "overall_fixture_rate": sum(1 for row in debug_rows if row.get("has_fixture")) / len(debug_rows) if debug_rows else 0.0,
        "overall_import_rate": sum(1 for row in debug_rows if row.get("has_cadquery_import")) / len(debug_rows) if debug_rows else 0.0,
    }

    fig, ax1 = plt.subplots(figsize=(10, 5.4), dpi=160)
    if xs:
        ax1.plot(xs, build_rate, label="build rate", linewidth=2.4, color="#0f766e")
        ax1.plot(xs, fixture_rate, label="has fixture", linewidth=2.0, color="#2563eb")
        ax1.plot(xs, import_rate, label="has cadquery import", linewidth=2.0, color="#9333ea")
        ax1.set_ylim(-0.05, 1.05)
        ax1.set_ylabel("rate")
        ax2 = ax1.twinx()
        ax2.plot(xs, avg_chars, label="avg code chars", linewidth=1.5, color="#f97316", alpha=0.7)
        ax2.set_ylabel("average code chars")
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="best")
    ax1.set_title("CADForge GRPO Code Health")
    ax1.set_xlabel("reward call")
    ax1.grid(True, alpha=0.25)
    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png)
    plt.close(fig)
    return summary


def plot_error_breakdown(debug_rows: list[dict[str, Any]], output_png: Path) -> dict[str, int]:
    import matplotlib.pyplot as plt

    counts: dict[str, int] = {}
    for row in debug_rows:
        key = str(row.get("error_kind") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:10]
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=160)
    if ordered:
        labels = [item[0] for item in ordered]
        values = [item[1] for item in ordered]
        ax.barh(labels[::-1], values[::-1], color="#64748b")
    ax.set_title("CADForge GRPO Error / Build Outcome Breakdown")
    ax.set_xlabel("completion count")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png)
    plt.close(fig)
    return counts


def latest_event_dir(output_dir: Path | None) -> Path | None:
    if output_dir is None or not output_dir.exists():
        return None
    files = sorted(output_dir.rglob("events.out.tfevents.*"), key=lambda path: path.stat().st_mtime)
    return files[-1].parent if files else None


def markdown_report(
    log_path: Path,
    rows: list[dict[str, Any]],
    train: list[tuple[int, float]],
    evals: list[tuple[int, float]],
    final: dict[str, Any],
    charts: dict[str, Path],
    scalars: dict[str, list[dict[str, float]]],
    debug_summary: dict[str, Any],
    reward_summary: dict[str, Any],
    error_counts: dict[str, int],
) -> str:
    first_loss = train[0][1] if train else None
    last_loss = train[-1][1] if train else None
    first_eval = evals[0][1] if evals else None
    last_eval = evals[-1][1] if evals else None
    lines = [
        "# CADForge Training Curves",
        "",
        f"- Log: `{log_path}`",
        f"- Parsed log metric rows: `{len(rows)}`",
        f"- TensorBoard scalar tags: `{len(scalars)}`",
        f"- Train steps logged: `{len(train)}`",
        f"- Eval points logged: `{len(evals)}`",
    ]
    if first_loss is not None and last_loss is not None:
        lines.append(f"- Train loss: `{first_loss:.4f}` -> `{last_loss:.4f}`")
    if first_eval is not None and last_eval is not None:
        lines.append(f"- Eval loss: `{first_eval:.4f}` -> `{last_eval:.4f}`")
    if reward_summary.get("points"):
        lines.extend([
            f"- GRPO reward points: `{reward_summary['points']}`",
            f"- GRPO mean/best reward: `{reward_summary.get('mean', 0.0):.4f}` / `{reward_summary.get('best', 0.0):.4f}`",
            f"- GRPO trend slope: `{reward_summary.get('slope') or 0.0:.6f}` per step",
        ])
    if debug_summary:
        lines.extend([
            f"- Completion debug rows: `{debug_summary.get('debug_rows', 0)}`",
            f"- Build rate from debug rows: `{debug_summary.get('overall_build_rate', 0.0):.1%}`",
            f"- Final fixture/import rates: `{debug_summary.get('overall_fixture_rate', 0.0):.1%}` / `{debug_summary.get('overall_import_rate', 0.0):.1%}`",
        ])
    if charts:
        lines.extend(["", "## Charts", ""])
        for label, path in charts.items():
            lines.append(f"![{label}]({path})")
    if final:
        lines.extend(["", "## Final Trainer Metrics", "", "```json", json.dumps(final, indent=2), "```"])
    if train:
        lines.extend(["", "## Recent Train Loss", "", "| step | loss |", "|---:|---:|"])
        for step, loss in train[-20:]:
            lines.append(f"| {step} | {loss:.4f} |")
    if evals:
        lines.extend(["", "## Eval Loss", "", "| step | eval_loss |", "|---:|---:|"])
        for step, loss in evals:
            lines.append(f"| {step} | {loss:.4f} |")
    if error_counts:
        lines.extend(["", "## GRPO Error Breakdown", "", "| outcome | count |", "|---|---:|"])
        for key, count in sorted(error_counts.items(), key=lambda item: item[1], reverse=True)[:12]:
            lines.append(f"| `{key}` | {count} |")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--event-dir", type=Path)
    parser.add_argument("--trainer-output-dir", type=Path)
    parser.add_argument("--debug-jsonl", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("training/reports/qwen35-2b-sft"))
    parser.add_argument("--title", default="CADForge Qwen Training")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = parse_metrics(args.log)
    event_dir = args.event_dir or latest_event_dir(args.trainer_output_dir)
    scalars = load_tensorboard_scalars(event_dir)
    debug_rows = parse_debug_jsonl(args.debug_jsonl)
    train, evals, final = split_series(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    charts: dict[str, Path] = {}
    has_loss_data = bool(
        train
        or evals
        or scalar_points(scalars, "loss", exclude=("eval", "grad", "reward"))
        or scalar_points(scalars, "eval", "loss")
    )
    if has_loss_data:
        charts["sft_loss_curve"] = args.output_dir / "sft_loss_curve.png"
        plot_loss_curves(train, evals, scalars, charts["sft_loss_curve"])

    timeline_chart = args.output_dir / "training_timeline.png"
    if plot_timeline(scalars, timeline_chart, f"{args.title} Wall-Clock Timeline"):
        charts["training_timeline"] = timeline_chart

    optimizer_chart = args.output_dir / "optimizer_health.png"
    plotted = plot_scalar_pair(
        scalars,
        optimizer_chart,
        "CADForge Optimizer Health",
        [
            ("learning rate", ("learning_rate",), ()),
            ("grad norm", ("grad_norm",), ()),
            ("entropy", ("entropy",), ()),
            ("clip ratio", ("clip_ratio",), ()),
            ("completion length", ("completion_length",), ()),
        ],
    )
    if plotted:
        charts["optimizer_health"] = optimizer_chart

    reward_chart = args.output_dir / "grpo_reward_curve.png"
    reward_summary = plot_reward_curve(scalars, debug_rows, reward_chart, f"{args.title} Reward Curve")
    if reward_summary.get("points"):
        charts["grpo_reward_curve"] = reward_chart

    debug_summary: dict[str, Any] = {}
    error_counts: dict[str, int] = {}
    if debug_rows:
        charts["grpo_code_health"] = args.output_dir / "grpo_code_health.png"
        debug_summary = plot_debug_health(debug_rows, charts["grpo_code_health"])
        charts["grpo_error_breakdown"] = args.output_dir / "grpo_error_breakdown.png"
        error_counts = plot_error_breakdown(debug_rows, charts["grpo_error_breakdown"])

    (args.output_dir / "metrics.json").write_text(json.dumps(rows, indent=2))
    (args.output_dir / "tensorboard_scalars.json").write_text(json.dumps(scalars, indent=2))
    if debug_rows:
        compact_debug = [
            {key: row.get(key) for key in ["reward_call", "index", "score", "task_id", "code_chars", "cadforge_build", "cadforge_total", "has_fixture", "has_cadquery_import", "error_kind"]}
            for row in debug_rows
        ]
        (args.output_dir / "debug_completion_summary.json").write_text(json.dumps(compact_debug, indent=2))
    (args.output_dir / "training_curve_report.md").write_text(
        markdown_report(args.log, rows, train, evals, final, charts, scalars, debug_summary, reward_summary, error_counts)
    )
    print(json.dumps({
        "rows": len(rows),
        "tensorboard_tags": len(scalars),
        "event_dir": str(event_dir) if event_dir else None,
        "debug_rows": len(debug_rows),
        "train_points": len(train),
        "eval_points": len(evals),
        "charts": {key: str(value) for key, value in charts.items()},
        "report": str(args.output_dir / "training_curve_report.md"),
    }, indent=2))


if __name__ == "__main__":
    main()
