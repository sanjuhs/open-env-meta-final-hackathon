#!/usr/bin/env python3
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "detailed-blog" / "rendered-assets"
RUNS = ROOT / "experiment-2-cadforge" / "runs" / "cadquery-env"

STATOR = RUNS / "local-judge-assets-strict-grpo-stator" / "model-output"
CASTER = RUNS / "local-judge-assets-strict-grpo-caster" / "model-output"
CHAIR_FAIL = RUNS / "local-judge-assets-strict-grpo-chair-fail" / "model-output"

WEAK_CASTER = (
    RUNS
    / "openai-gpt-5.4-caster_wheel_fork-bad_dimensions-2026-04-25T13-20-57-868Z"
    / "seed"
)

REFERENCE_CASTER = (
    ROOT
    / "experiment-2-cadforge"
    / "data"
    / "reference-metrics"
    / "caster_wheel_fork"
    / "glb_reference"
    / "silhouettes"
    / "isometric.png"
)


BG = (247, 249, 250)
INK = (27, 35, 43)
MUTED = (91, 103, 114)
LINE = (214, 222, 230)
ACCENT = (45, 112, 145)
GOOD = (52, 135, 88)
BAD = (192, 76, 67)
CODE_BG = (18, 24, 32)
CODE_FG = (226, 235, 243)


def mpl_color(color: tuple[int, int, int]) -> tuple[float, float, float]:
    return tuple(channel / 255 for channel in color)


def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if mono:
        candidates += [
            "/System/Library/Fonts/Menlo.ttc",
            "/Library/Fonts/Menlo.ttc",
        ]
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


FONT_H1 = font(34, bold=True)
FONT_H2 = font(22, bold=True)
FONT_BODY = font(18)
FONT_SMALL = font(15)
FONT_MONO = font(16, mono=True)
FONT_MONO_SMALL = font(14, mono=True)


def fit_image(path: Path, size: tuple[int, int], bg: tuple[int, int, int] = BG) -> Image.Image:
    img = Image.open(path).convert("RGB")
    img.thumbnail((size[0] - 24, size[1] - 24), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, bg)
    x = (size[0] - img.width) // 2
    y = (size[1] - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def rounded_card(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], fill=(255, 255, 255)) -> None:
    draw.rounded_rectangle(xy, radius=8, fill=fill, outline=LINE, width=2)


def draw_title(draw: ImageDraw.ImageDraw, title: str, subtitle: str | None = None) -> None:
    draw.text((42, 28), title, fill=INK, font=FONT_H1)
    if subtitle:
        draw.text((42, 72), subtitle, fill=MUTED, font=FONT_BODY)


def render_grid(title: str, subtitle: str, root: Path, out_name: str) -> Path:
    views = [
        ("isometric", "Isometric"),
        ("top", "Top"),
        ("front", "Front"),
        ("left", "Left"),
    ]
    w, h = 1480, 1060
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    draw_title(draw, title, subtitle)

    card_w, card_h = 680, 415
    positions = [(42, 126), (758, 126), (42, 594), (758, 594)]
    for (view, label), (x, y) in zip(views, positions):
        rounded_card(draw, (x, y, x + card_w, y + card_h))
        draw.text((x + 24, y + 20), label, fill=INK, font=FONT_H2)
        render = fit_image(root / "renders" / f"{view}.png", (card_w - 48, card_h - 74), (255, 255, 255))
        img.paste(render, (x + 24, y + 62))

    out = OUT / out_name
    img.save(out)
    return out


def metric_line(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, value: str, color=INK) -> int:
    draw.text((x, y), label, fill=MUTED, font=FONT_SMALL)
    draw.text((x + 170, y), value, fill=color, font=FONT_SMALL)
    return y + 28


def render_before_after() -> Path:
    w, h = 1480, 760
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    draw_title(
        draw,
        "Same Task: Weak CAD Seed vs Strict GRPO Output",
        "The left side is a deliberately weak caster seed; the right side is the strict GRPO held-out caster build.",
    )
    panels = [
        (WEAK_CASTER / "renders" / "isometric.png", "Weak seed", "builds, but weaker task fit", BAD),
        (CASTER / "renders" / "isometric.png", "Strict GRPO output", "build = 1.0, editable = 0.942", GOOD),
    ]
    for i, (path, heading, sub, color) in enumerate(panels):
        x = 42 + i * 716
        y = 126
        rounded_card(draw, (x, y, x + 680, y + 580))
        draw.rectangle((x, y, x + 680, y + 8), fill=color)
        draw.text((x + 24, y + 26), heading, fill=INK, font=FONT_H2)
        draw.text((x + 24, y + 56), sub, fill=MUTED, font=FONT_BODY)
        panel = fit_image(path, (632, 470), (255, 255, 255))
        img.paste(panel, (x + 24, y + 94))
    out = OUT / "before-after-caster-weak-vs-strict-grpo.png"
    img.save(out)
    return out


def text_image(title: str, subtitle: str, lines: list[str], out_name: str, highlight_last: bool = False) -> Path:
    w, h = 1480, 960
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    draw_title(draw, title, subtitle)
    x, y = 42, 126
    rounded_card(draw, (x, y, w - 42, h - 42), CODE_BG)
    ty = y + 30
    for idx, line in enumerate(lines):
        fill = (255, 177, 166) if highlight_last and idx == len(lines) - 1 else CODE_FG
        draw.text((x + 30, ty), line[:150], fill=fill, font=FONT_MONO)
        ty += 24
        if ty > h - 72:
            break
    out = OUT / out_name
    img.save(out)
    return out


def render_chair_failure() -> Path:
    code = (CHAIR_FAIL / "candidate.py").read_text().splitlines()
    start = max(0, len(code) - 22)
    numbered = [f"{i + 1:>3}  {line}" for i, line in enumerate(code[start:], start=start)]
    numbered.append("")
    numbered.append("Build error: SyntaxError: '(' was never closed")
    return text_image(
        "Held-Out Chair Failure: Clipped Final Assembly",
        "The model wrote plausible chair code, then stopped before closing the final union.",
        numbered,
        "failed-chair-clipped-code.png",
        highlight_last=True,
    )


def render_reward_json() -> Path:
    reward = json.loads((CASTER / "reward.json").read_text())
    small = {
        "ok": reward["ok"],
        "task": "caster_wheel_fork",
        "reward": reward["reward"],
        "notes": reward["notes"][:2],
    }
    lines = json.dumps(small, indent=2).splitlines()
    return text_image(
        "Successful Build: CADForge Reward JSON",
        "The environment returns structured reward dimensions, not a vague text preference.",
        lines,
        "successful-build-reward-json.png",
    )


def render_traceback_json() -> Path:
    reward = json.loads((CHAIR_FAIL / "reward.json").read_text())
    small = {
        "ok": reward["ok"],
        "task": "four_leg_chair_700n",
        "failure_class": "syntax_closure",
        "reward": reward["reward"],
        "notes": reward["notes"],
    }
    lines = json.dumps(small, indent=2).splitlines()
    return text_image(
        "Failed Build: Failure Class Becomes Training Signal",
        "This is the kind of verifier output that seeds the adaptive repair curriculum.",
        lines,
        "failed-build-traceback-json.png",
        highlight_last=False,
    )


def render_code_beside_stl() -> Path:
    w, h = 1480, 860
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    draw_title(
        draw,
        "Editable CadQuery Output Beside Rendered STL",
        "The artifact is parameterized code that exports geometry, not a one-off mesh blob.",
    )
    left = (42, 126, 742, 804)
    right = (778, 126, 1438, 804)
    rounded_card(draw, left, CODE_BG)
    rounded_card(draw, right)
    code = (CASTER / "candidate.py").read_text().splitlines()
    excerpt = []
    for line in code[:90]:
        if any(key in line for key in ["plate_w", "stem_d", "fork_inside_w", "wheel_d", "def make_", "fixture ="]):
            excerpt.append(line)
    excerpt = excerpt[:22]
    ty = left[1] + 28
    for line in excerpt:
        draw.text((left[0] + 28, ty), line[:82], fill=CODE_FG, font=FONT_MONO_SMALL)
        ty += 25
    draw.text((right[0] + 24, right[1] + 24), "Rendered STL", fill=INK, font=FONT_H2)
    render = fit_image(CASTER / "renders" / "isometric.png", (right[2] - right[0] - 48, right[3] - right[1] - 84), (255, 255, 255))
    img.paste(render, (right[0] + 24, right[1] + 68))
    out = OUT / "cadquery-code-beside-render.png"
    img.save(out)
    return out


def render_reference_vs_cadquery() -> Path:
    w, h = 1480, 740
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    draw_title(
        draw,
        "Reference Signal vs Generated Code-CAD",
        "A GLB-derived silhouette/reference can become reward signal while the model still outputs editable CadQuery.",
    )
    panels = [
        (REFERENCE_CASTER, "GLB reference silhouette"),
        (CASTER / "renders" / "isometric.png", "Generated CadQuery render"),
    ]
    for i, (path, heading) in enumerate(panels):
        x = 42 + i * 716
        y = 126
        rounded_card(draw, (x, y, x + 680, y + 550))
        draw.text((x + 24, y + 24), heading, fill=INK, font=FONT_H2)
        panel = fit_image(path, (632, 455), (255, 255, 255))
        img.paste(panel, (x + 24, y + 74))
    out = OUT / "glb-reference-vs-cadquery-render.png"
    img.save(out)
    return out


def render_build_rate_chart() -> Path:
    labels = [
        "Dense GRPO\n2B",
        "Dense GRPO\n9B",
        "Early adaptive\nrepair",
        "Strict GRPO\n9B",
        "Final adaptive\nrepair",
        "Held-out\neval",
    ]
    values = [0, 0, 0, 30.0, 29.4, 66.7]
    colors = [BAD, BAD, BAD, ACCENT, ACCENT, GOOD]
    plt.figure(figsize=(10, 5.6), dpi=180)
    bars = plt.bar(labels, values, color=[tuple(c / 255 for c in color) for color in colors])
    plt.ylim(0, 80)
    plt.ylabel("Build rate (%)")
    plt.title("Buildability Across CADForge Training Milestones")
    plt.grid(axis="y", alpha=0.22)
    for bar, value in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width() / 2, value + 2, f"{value:g}%", ha="center", fontsize=11)
    plt.tight_layout()
    out = OUT / "build-rate-comparison.png"
    plt.savefig(out, facecolor=mpl_color(BG))
    plt.close()
    return out


def render_failure_class_chart() -> Path:
    data = {
        "syntax closure": 110,
        "type/value/kernel": 47,
        "weak geometry": 26,
        "undefined names": 20,
        "invented API": 17,
        "missing fixture": 15,
        "unknown build": 15,
        "low editability": 4,
    }
    labels = list(data.keys())[::-1]
    values = list(data.values())[::-1]
    plt.figure(figsize=(10, 5.6), dpi=180)
    plt.barh(labels, values, color=tuple(c / 255 for c in ACCENT))
    plt.xlabel("Repair rows mined from strict GRPO rollouts")
    plt.title("Adaptive Curriculum Finds The Next Bottleneck")
    plt.grid(axis="x", alpha=0.22)
    for i, value in enumerate(values):
        plt.text(value + 2, i, str(value), va="center", fontsize=10)
    plt.tight_layout()
    out = OUT / "adaptive-curriculum-failure-classes.png"
    plt.savefig(out, facecolor=mpl_color(BG))
    plt.close()
    return out


def render_loop_summary() -> Path:
    w, h = 1480, 840
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    draw_title(draw, "CADForge Self-Improvement Loops", "Two loops turn CAD failures and reference assets into training signal.")
    boxes = [
        (90, 160, "Rollout", "model writes CadQuery"),
        (420, 160, "Verifier", "compile, export, reward"),
        (750, 160, "Failure mining", "classify what broke"),
        (1080, 160, "Next batch", "repair curriculum"),
        (255, 520, "Prompt/image", "generate object references"),
        (585, 520, "GLB metrics", "bbox, silhouette, points"),
        (915, 520, "Reference reward", "align editable CAD"),
    ]
    for x, y, title, sub in boxes:
        rounded_card(draw, (x, y, x + 260, y + 140))
        draw.text((x + 22, y + 28), title, fill=INK, font=FONT_H2)
        for j, line in enumerate(textwrap.wrap(sub, width=23)):
            draw.text((x + 22, y + 72 + 24 * j), line, fill=MUTED, font=FONT_BODY)
    arrows = [
        ((350, 230), (420, 230)),
        ((680, 230), (750, 230)),
        ((1010, 230), (1080, 230)),
        ((1210, 300), (220, 300), (220, 230), (90, 230)),
        ((515, 590), (585, 590)),
        ((845, 590), (915, 590)),
        ((1045, 520), (1045, 320)),
    ]
    for arrow in arrows:
        if len(arrow) == 2:
            draw.line([arrow[0], arrow[1]], fill=ACCENT, width=4)
            end = arrow[1]
        else:
            draw.line(list(arrow), fill=ACCENT, width=4, joint="curve")
            end = arrow[-1]
        draw.polygon([(end[0], end[1]), (end[0] - 14, end[1] - 8), (end[0] - 14, end[1] + 8)], fill=ACCENT)
    out = OUT / "self-improvement-loop-summary.png"
    img.save(out)
    return out


def write_index(paths: list[Path]) -> Path:
    supplemental = [
        OUT / "hugging-face-space-demo-ui.png",
        OUT / "hugging-face-space-repair-loop-ui.png",
        OUT / "hugging-face-space-repair-loop-metrics.png",
        OUT / "hugging-face-space-repair-loop-lower.png",
        OUT / "hugging-face-space-repair-loop-fullpage.png",
    ]
    all_paths = [*paths, *(path for path in supplemental if path.exists())]
    coverage = [
        ("strict GRPO generated stator render", "strict-grpo-stator-render.png"),
        ("strict GRPO generated caster fork render", "strict-grpo-caster-render.png"),
        ("failed held-out chair/clipped-code example", "failed-chair-clipped-code.png"),
        ("before/after weak vs strict GRPO comparison", "before-after-caster-weak-vs-strict-grpo.png"),
        ("successful reward JSON", "successful-build-reward-json.png"),
        ("failed build traceback/reward JSON", "failed-build-traceback-json.png"),
        ("demo UI screenshot", "hugging-face-space-repair-loop-ui.png"),
        ("CadQuery snippet beside rendered STL", "cadquery-code-beside-render.png"),
        ("GLB reference beside generated CadQuery render", "glb-reference-vs-cadquery-render.png"),
        ("build-rate comparison chart", "build-rate-comparison.png"),
        ("adaptive curriculum failure-class chart", "adaptive-curriculum-failure-classes.png"),
        ("self-improvement loop summary", "self-improvement-loop-summary.png"),
    ]
    lines = [
        "# CADForge Rendered Blog Assets",
        "",
        "Generated locally from CADForge artifacts.",
        "",
    ]
    for path in all_paths:
        rel = path.relative_to(OUT.parent)
        lines.append(f"- `{rel}`")
    lines.extend(
        [
            "",
            "## Coverage",
            "",
            "The current asset pack covers the required evidence:",
            "",
            "| Visual | Asset |",
            "|---|---|",
        ]
    )
    existing = {path.name for path in all_paths}
    for label, filename in coverage:
        if filename in existing:
            lines.append(f"| {label} | `{filename}` |")
    lines.extend(
        [
            "",
            "Supplemental inference comparison:",
            "",
            "- `../../inference/results/stator-qwen-vs-frontier/comparison.png`",
        ]
    )
    index = OUT / "README.md"
    index.write_text("\n".join(lines) + "\n")
    return index


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [
        render_grid(
            "Strict GRPO Generated Stator Render",
            "Held-out axial motor stator: buildable CadQuery with ring, teeth, and shaft opening.",
            STATOR,
            "strict-grpo-stator-render.png",
        ),
        render_grid(
            "Strict GRPO Generated Caster Fork Render",
            "Held-out caster assembly: wheel, fork, axle, stem, and top mounting plate.",
            CASTER,
            "strict-grpo-caster-render.png",
        ),
        render_chair_failure(),
        render_before_after(),
        render_reward_json(),
        render_traceback_json(),
        render_code_beside_stl(),
        render_reference_vs_cadquery(),
        render_build_rate_chart(),
        render_failure_class_chart(),
        render_loop_summary(),
    ]
    index = write_index(paths)
    print(json.dumps({"out_dir": str(OUT), "index": str(index), "assets": [str(path) for path in paths]}, indent=2))


if __name__ == "__main__":
    main()
