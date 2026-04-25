from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import trimesh
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
MODELS_ROOT = REPO_ROOT / "3d-models"
RUNS_ROOT = APP_ROOT / "runs" / "cadquery-env"
REFERENCE_ROOT = APP_ROOT / "runs" / "cadquery-reference"
RUNNER = APP_ROOT / "python_tools" / "cadquery_code_runner.py"
DEFAULT_GLB = MODELS_ROOT / "ikea_markus_office_chair.glb"
DEFAULT_IDEAL_CODE = MODELS_ROOT / "ikea_markus_idealish_code.md"
DEFAULT_TASKS = APP_ROOT / "data" / "cad_tasks.json"

VIEWS = {
    "front": {"axes": (0, 2), "flip_x": False},
    "back": {"axes": (0, 2), "flip_x": True},
    "left": {"axes": (1, 2), "flip_x": False},
    "right": {"axes": (1, 2), "flip_x": True},
    "top": {"axes": (0, 1), "flip_x": False},
}

SEMANTIC_HINTS = [
    "seat",
    "backrest",
    "headrest",
    "armrest",
    "gas_cylinder",
    "central_column",
    "star_base",
    "caster",
    "lumbar",
    "mechanism",
]


@dataclass(frozen=True)
class MeshBundle:
    mesh: trimesh.Trimesh
    normalized: trimesh.Trimesh
    bbox: dict[str, float]


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-")
    return slug[:80] or "run"


def extract_code(text: str) -> str:
    match = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.IGNORECASE | re.DOTALL)
    return (match.group(1) if match else text).strip()


def read_code(path: Path) -> str:
    return extract_code(path.read_text())


def read_task_spec(path_or_id: str | None) -> dict[str, Any] | None:
    if not path_or_id:
        return None
    path = Path(path_or_id)
    if path.exists():
        return json.loads(path.read_text())
    if DEFAULT_TASKS.exists():
        for task in json.loads(DEFAULT_TASKS.read_text()):
            if task.get("id") == path_or_id:
                return task
    raise FileNotFoundError(f"Task spec not found: {path_or_id}")


def concise_error(stdout: str = "", stderr: str = "") -> str:
    text = (stderr or stdout or "").strip()
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        if re.search(r"(Error|Exception|Traceback|NameError|TypeError|ValueError|AttributeError|ImportError|RuntimeError)", line):
            return line[:500]
    return lines[-1][:500] if lines else ""


def mesh_from_file(path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(path, force="scene")
    if isinstance(loaded, trimesh.Scene):
        mesh = loaded.to_geometry() if hasattr(loaded, "to_geometry") else loaded.dump(concatenate=True)
    else:
        mesh = loaded
    if isinstance(mesh, list):
        mesh = trimesh.util.concatenate(mesh)
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"Could not load mesh from {path}")
    mesh = mesh.copy()
    mesh.remove_unreferenced_vertices()
    return mesh


def canonicalize_largest_axis_to_z(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    canonical = mesh.copy()
    bounds = np.asarray(canonical.bounds, dtype=float)
    dims = bounds[1] - bounds[0]
    up_axis = int(np.argmax(dims))
    if up_axis == 2:
        return canonical

    vertices = np.asarray(canonical.vertices, dtype=float).copy()
    if up_axis == 1:
        # Common GLB convention for this asset: Y is vertical.
        vertices = vertices[:, [0, 2, 1]]
    elif up_axis == 0:
        vertices = vertices[:, [1, 2, 0]]
    canonical.vertices = vertices
    canonical.remove_unreferenced_vertices()
    return canonical


def bbox_dict(mesh: trimesh.Trimesh) -> dict[str, float]:
    bounds = np.asarray(mesh.bounds, dtype=float)
    dims = bounds[1] - bounds[0]
    return {
        "xmin": float(bounds[0, 0]),
        "xmax": float(bounds[1, 0]),
        "ymin": float(bounds[0, 1]),
        "ymax": float(bounds[1, 1]),
        "zmin": float(bounds[0, 2]),
        "zmax": float(bounds[1, 2]),
        "xlen": float(dims[0]),
        "ylen": float(dims[1]),
        "zlen": float(dims[2]),
    }


def normalize_mesh(mesh: trimesh.Trimesh, target_height: float = 1000.0) -> trimesh.Trimesh:
    normalized = mesh.copy()
    bounds = np.asarray(normalized.bounds, dtype=float)
    dims = bounds[1] - bounds[0]
    height = float(max(dims[2], 1e-9))
    scale = target_height / height
    normalized.apply_scale(scale)
    bounds = np.asarray(normalized.bounds, dtype=float)
    center_xy = (bounds[0, :2] + bounds[1, :2]) / 2.0
    normalized.apply_translation([-center_xy[0], -center_xy[1], -bounds[0, 2]])
    normalized.remove_unreferenced_vertices()
    return normalized


def mesh_bundle(path: Path) -> MeshBundle:
    mesh = mesh_from_file(path)
    normalized = normalize_mesh(mesh)
    return MeshBundle(mesh=mesh, normalized=normalized, bbox=bbox_dict(mesh))


def run_cadquery(code: str, out_dir: Path, name: str, timeout: int = 180) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--out-dir", str(out_dir), "--name", safe_slug(name)],
        cwd=APP_ROOT,
        input=json.dumps({"code": code}),
        text=True,
        capture_output=True,
        timeout=timeout,
        env={
            **dict(**__import__("os").environ),
            "PYTHONPATH": str(APP_ROOT / "python_tools"),
            "XDG_CACHE_HOME": str(APP_ROOT / ".cache"),
        },
    )
    elapsed_ms = int((time.time() - started) * 1000)
    output: dict[str, Any] | None = None
    if proc.returncode == 0:
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        if lines:
            output = json.loads(lines[-1])
    return {
        "ok": proc.returncode == 0 and output is not None,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "elapsed_ms": elapsed_ms,
        "output": output,
    }


def edge_counts(mesh: trimesh.Trimesh) -> tuple[int, int]:
    if len(mesh.faces) == 0:
        return 0, 0
    inverse = mesh.edges_unique_inverse
    counts = np.bincount(inverse, minlength=len(mesh.edges_unique))
    boundary_edges = int(np.sum(counts == 1))
    non_manifold_edges = int(np.sum(counts > 2))
    return boundary_edges, non_manifold_edges


def topology_metrics(mesh: trimesh.Trimesh) -> dict[str, Any]:
    components = mesh.split(only_watertight=False)
    boundary_edges, non_manifold_edges = edge_counts(mesh)
    area_faces = np.asarray(mesh.area_faces) if len(mesh.faces) else np.array([])
    degenerate_faces = int(np.sum(area_faces < 1e-8))
    return {
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "components": int(len(components)),
        "floating_components": int(max(0, len(components) - 1)),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "boundary_edges": boundary_edges,
        "non_manifold_edges": non_manifold_edges,
        "degenerate_faces": degenerate_faces,
    }


def topology_reward(metrics: dict[str, Any]) -> dict[str, Any]:
    # Markus is an assembly benchmark: a good chair can contain many valid solids.
    # For monolithic hooks/brackets we can add a stricter single-body reward later.
    component_count = metrics["components"]
    component_score = 0.0
    if 1 <= component_count <= 120:
        component_score = 0.25
    elif component_count <= 250:
        component_score = 0.12

    face_count = max(1, metrics["faces"])
    boundary_ratio = metrics["boundary_edges"] / max(1, metrics["faces"])
    non_manifold_ratio = metrics["non_manifold_edges"] / face_count
    degenerate_ratio = metrics["degenerate_faces"] / face_count

    score = 0.0
    score += component_score
    score += 0.15 if metrics["watertight"] else 0.05
    score += 0.20 * max(0.0, 1.0 - boundary_ratio * 250.0)
    score += 0.15 * max(0.0, 1.0 - non_manifold_ratio * 250.0)
    score += 0.15 * max(0.0, 1.0 - degenerate_ratio * 250.0)
    score += 0.10 if 50 <= metrics["faces"] <= 750000 else 0.03
    penalties = {
        "too_many_components_penalty": -0.20 if component_count > 250 else 0.0,
        "high_boundary_ratio_penalty": -0.10 if boundary_ratio > 0.02 else 0.0,
        "high_non_manifold_ratio_penalty": -0.10 if non_manifold_ratio > 0.02 else 0.0,
        "high_degenerate_ratio_penalty": -0.10 if degenerate_ratio > 0.02 else 0.0,
    }
    return {"score": float(max(0.0, min(1.0, score + sum(penalties.values())))), "penalties": penalties}


def bbox_gap(a: np.ndarray, b: np.ndarray) -> float:
    lower_gap = np.maximum(a[0] - b[1], 0.0)
    upper_gap = np.maximum(b[0] - a[1], 0.0)
    return float(np.linalg.norm(np.maximum(lower_gap, upper_gap)))


def contact_metrics(mesh: trimesh.Trimesh) -> dict[str, Any]:
    components = list(mesh.split(only_watertight=False))
    if len(components) <= 1:
        return {
            "score": 1.0,
            "components_checked": len(components),
            "mean_gap_ratio": 0.0,
            "max_gap_ratio": 0.0,
            "large_gap_components": 0,
        }

    bounds = []
    root_bbox = bbox_dict(mesh)
    height = max(root_bbox["zlen"], 1e-9)
    for component in components:
        bbox = np.asarray(component.bounds, dtype=float)
        dims = bbox[1] - bbox[0]
        diag = float(np.linalg.norm(dims))
        # Ignore tiny mesh shards from tessellation/import noise.
        if diag >= 0.015 * height:
            bounds.append((bbox, diag))
    if len(bounds) <= 1:
        return {
            "score": 1.0,
            "components_checked": len(bounds),
            "mean_gap_ratio": 0.0,
            "max_gap_ratio": 0.0,
            "large_gap_components": 0,
        }

    gaps = []
    for i, (bbox, _diag) in enumerate(bounds):
        nearest = min(bbox_gap(bbox, other_bbox) for j, (other_bbox, _other_diag) in enumerate(bounds) if i != j)
        gaps.append(nearest / height)
    gaps_array = np.asarray(gaps, dtype=float)
    mean_gap = float(np.mean(gaps_array))
    max_gap = float(np.max(gaps_array))
    large_gap_components = int(np.sum(gaps_array > 0.08))
    score = math.exp(-mean_gap * 28.0) * math.exp(-max_gap * 4.0)
    score -= min(0.40, large_gap_components * 0.04)
    return {
        "score": float(max(0.0, min(1.0, score))),
        "components_checked": len(bounds),
        "mean_gap_ratio": mean_gap,
        "max_gap_ratio": max_gap,
        "large_gap_components": large_gap_components,
    }


def project_vertices(vertices: np.ndarray, view: str) -> np.ndarray:
    if view == "isometric":
        rz = math.radians(42)
        rx = math.radians(58)
        rot_z = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]])
        rot_x = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
        rotated = vertices @ (rot_z @ rot_x).T
        return rotated[:, [0, 2]]
    spec = VIEWS[view]
    pts = vertices[:, list(spec["axes"])]
    if spec["flip_x"]:
        pts = pts.copy()
        pts[:, 0] *= -1
    return pts


def silhouette_mask(mesh: trimesh.Trimesh, view: str, size: int = 512, padding: int = 28) -> Image.Image:
    pts = project_vertices(np.asarray(mesh.vertices, dtype=float), view)
    mins = pts.min(axis=0)
    maxs = pts.max(axis=0)
    span = np.maximum(maxs - mins, 1e-9)
    scale = (size - 2 * padding) / float(max(span))
    xy = (pts - mins) * scale + padding
    xy[:, 1] = size - xy[:, 1]
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    for face in mesh.faces:
        poly = [(float(xy[i, 0]), float(xy[i, 1])) for i in face]
        draw.polygon(poly, fill=255)
    return image


def view_depth(vertices: np.ndarray, view: str) -> np.ndarray:
    if view == "front":
        return vertices[:, 1]
    if view == "back":
        return -vertices[:, 1]
    if view == "left":
        return vertices[:, 0]
    if view == "right":
        return -vertices[:, 0]
    if view == "top":
        return vertices[:, 2]
    return vertices @ np.array([0.42, -0.55, 0.72])


def projected_image_points(mesh: trimesh.Trimesh, view: str, size: int = 720, padding: int = 42) -> np.ndarray:
    pts = project_vertices(np.asarray(mesh.vertices, dtype=float), view)
    mins = pts.min(axis=0)
    maxs = pts.max(axis=0)
    span = np.maximum(maxs - mins, 1e-9)
    scale = (size - 2 * padding) / float(max(span))
    xy = (pts - mins) * scale + padding
    xy[:, 1] = size - xy[:, 1]
    return xy


def color_render_image(mesh: trimesh.Trimesh, view: str, size: int = 720, padding: int = 42) -> Image.Image:
    vertices = np.asarray(mesh.vertices, dtype=float)
    xy = projected_image_points(mesh, view, size=size, padding=padding)
    depths = view_depth(vertices, view)
    face_depths = depths[mesh.faces].mean(axis=1)
    order = np.argsort(face_depths)
    z_values = vertices[:, 2]
    zmin = float(z_values.min())
    zspan = float(max(z_values.max() - zmin, 1e-9))

    image = Image.new("RGB", (size, size), (244, 247, 250))
    draw = ImageDraw.Draw(image)
    grid = (222, 228, 235)
    for value in range(0, size, 72):
        draw.line([(value, 0), (value, size)], fill=grid)
        draw.line([(0, value), (size, value)], fill=grid)

    palette = [
        np.array([82, 111, 135]),
        np.array([94, 147, 113]),
        np.array([198, 95, 73]),
        np.array([207, 151, 63]),
        np.array([92, 124, 181]),
    ]
    for face_index in order:
        face = mesh.faces[face_index]
        center_z = float(vertices[face, 2].mean())
        height_mix = (center_z - zmin) / zspan
        base = palette[int(height_mix * (len(palette) - 1)) % len(palette)]
        shade = 0.68 + 0.32 * height_mix
        color = tuple(np.clip(base * shade + 20, 0, 255).astype(int).tolist())
        poly = [(float(xy[i, 0]), float(xy[i, 1])) for i in face]
        draw.polygon(poly, fill=color, outline=(63, 78, 92))

    draw.rectangle([0, 0, size - 1, size - 1], outline=(210, 218, 228), width=2)
    return image


def save_silhouettes(mesh: trimesh.Trimesh, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for view in [*VIEWS.keys(), "isometric"]:
        image = silhouette_mask(mesh, view)
        path = out_dir / f"{view}.png"
        image.save(path)
        paths[view] = str(path)
    return paths


def save_color_renders(mesh: trimesh.Trimesh, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for view in [*VIEWS.keys(), "isometric"]:
        image = color_render_image(mesh, view)
        path = out_dir / f"{view}.png"
        image.save(path)
        paths[view] = str(path)
    return paths


def mask_iou(a_path: Path, b_path: Path) -> float:
    a = np.asarray(Image.open(a_path).convert("L")) > 0
    b = np.asarray(Image.open(b_path).convert("L")) > 0
    union = np.logical_or(a, b).sum()
    if union == 0:
        return 0.0
    return float(np.logical_and(a, b).sum() / union)


def sample_points(mesh: trimesh.Trimesh, count: int = 3000) -> np.ndarray:
    state = np.random.get_state()
    np.random.seed(7)
    try:
        points = mesh.sample(count)
    finally:
        np.random.set_state(state)
    return np.asarray(points, dtype=np.float32)


def save_reference_mesh(name: str, mesh: trimesh.Trimesh, root: Path) -> dict[str, Any]:
    ref_dir = root / name
    ref_dir.mkdir(parents=True, exist_ok=True)
    normalized = normalize_mesh(mesh)
    stl_path = ref_dir / f"{name}_normalized.stl"
    normalized.export(stl_path)
    silhouettes = save_silhouettes(normalized, ref_dir / "silhouettes")
    points = sample_points(normalized)
    points_path = ref_dir / "points.npy"
    np.save(points_path, points)
    metrics = {
        "name": name,
        "stl_path": str(stl_path),
        "points_path": str(points_path),
        "silhouettes": silhouettes,
        "bbox": bbox_dict(mesh),
        "normalized_bbox": bbox_dict(normalized),
        "topology": topology_metrics(normalized),
    }
    (ref_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics


def preprocess_reference(glb_path: Path, ideal_code_path: Path | None = DEFAULT_IDEAL_CODE, out_root: Path = REFERENCE_ROOT) -> dict[str, Any]:
    out_root.mkdir(parents=True, exist_ok=True)
    glb_mesh = canonicalize_largest_axis_to_z(mesh_from_file(glb_path))
    glb_metrics = save_reference_mesh("glb_reference", glb_mesh, out_root)

    ideal_metrics = None
    correlation = None
    if ideal_code_path is not None and ideal_code_path.exists():
        ideal_code = read_code(ideal_code_path)
        ideal_run_dir = out_root / "ideal_cadquery_run"
        ideal_run = run_cadquery(ideal_code, ideal_run_dir, "ideal_cadquery")
        if not ideal_run["ok"]:
            raise RuntimeError(f"Ideal CadQuery reference failed: {ideal_run['stderr'] or ideal_run['stdout']}")
        ideal_stl = Path(ideal_run["output"]["stl_path"])
        ideal_mesh = mesh_from_file(ideal_stl)
        ideal_metrics = save_reference_mesh("ideal_cadquery", ideal_mesh, out_root)
        correlation = compare_to_references(normalize_mesh(ideal_mesh), out_root, include_ideal=False, mode="full")

    summary = {
        "source_glb": str(glb_path),
        "source_ideal_code": str(ideal_code_path) if ideal_code_path else None,
        "glb_reference": glb_metrics,
        "ideal_cadquery": ideal_metrics,
        "ideal_vs_glb_correlation": correlation,
        "semantic_hints": SEMANTIC_HINTS,
    }
    (out_root / "reference_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def load_reference_summary(root: Path = REFERENCE_ROOT, auto_default: bool = True) -> dict[str, Any]:
    path = root / "reference_summary.json"
    if not path.exists():
        if not auto_default:
            return {}
        return preprocess_reference(DEFAULT_GLB, DEFAULT_IDEAL_CODE, root)
    return json.loads(path.read_text())


def bbox_similarity(candidate_bbox: dict[str, float], ref_bbox: dict[str, float]) -> float:
    cand = np.array([candidate_bbox["xlen"], candidate_bbox["ylen"], candidate_bbox["zlen"]], dtype=float)
    ref = np.array([ref_bbox["xlen"], ref_bbox["ylen"], ref_bbox["zlen"]], dtype=float)
    cand = cand / max(cand[2], 1e-9)
    ref = ref / max(ref[2], 1e-9)
    err = float(np.mean(np.abs(cand - ref) / np.maximum(ref, 1e-9)))
    return float(max(0.0, 1.0 - err))


def chamfer_score(candidate_points: np.ndarray, ref_points_path: Path) -> float:
    ref_points = np.load(ref_points_path)
    cand_tree = cKDTree(candidate_points)
    ref_tree = cKDTree(ref_points)
    d1 = cand_tree.query(ref_points, k=1, workers=-1)[0]
    d2 = ref_tree.query(candidate_points, k=1, workers=-1)[0]
    chamfer = float((np.mean(d1) + np.mean(d2)) / 2.0)
    normalized = chamfer / 1000.0
    return float(math.exp(-normalized / 0.10))


def silhouette_scores(candidate_silhouettes: dict[str, str], ref_silhouettes: dict[str, str]) -> dict[str, Any]:
    per_view = {}
    for view, path in candidate_silhouettes.items():
        if view in ref_silhouettes:
            per_view[view] = mask_iou(Path(path), Path(ref_silhouettes[view]))
    weights = {"front": 0.18, "back": 0.12, "left": 0.18, "right": 0.18, "top": 0.14, "isometric": 0.20}
    total = sum(per_view.get(view, 0.0) * weight for view, weight in weights.items())
    return {"score": float(total), "per_view": per_view}


def compare_to_reference_name(
    candidate: trimesh.Trimesh,
    candidate_silhouettes: dict[str, str] | None,
    root: Path,
    name: str,
    mode: str,
) -> dict[str, Any]:
    metrics = json.loads((root / name / "metrics.json").read_text())
    bbox = bbox_similarity(bbox_dict(candidate), metrics["normalized_bbox"])
    if mode == "fast":
        return {
            "bbox": bbox,
            "chamfer": bbox,
            "silhouette": {"score": bbox, "per_view": {}},
        }
    if candidate_silhouettes is None:
        raise ValueError("Full reference comparison requires candidate silhouettes.")
    cand_points = sample_points(candidate, count=1500)
    return {
        "bbox": bbox,
        "chamfer": chamfer_score(cand_points, Path(metrics["points_path"])),
        "silhouette": silhouette_scores(candidate_silhouettes, metrics["silhouettes"]),
    }


def compare_to_references(
    candidate: trimesh.Trimesh,
    root: Path,
    include_ideal: bool = True,
    mode: str = "full",
    candidate_silhouettes: dict[str, str] | None = None,
) -> dict[str, Any]:
    if mode not in {"fast", "full"}:
        raise ValueError(f"Unknown reward mode: {mode}")
    if mode == "full" and candidate_silhouettes is None:
        temp_dir = root / "_tmp_compare"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        candidate_silhouettes = save_silhouettes(candidate, temp_dir / "silhouettes")
    glb = compare_to_reference_name(candidate, candidate_silhouettes, root, "glb_reference", mode)
    result = {"glb_reference": glb}
    if include_ideal and (root / "ideal_cadquery" / "metrics.json").exists():
        ideal = compare_to_reference_name(candidate, candidate_silhouettes, root, "ideal_cadquery", mode)
        result["ideal_cadquery"] = ideal
    return result


def semantic_reward(code: str, mesh: trimesh.Trimesh, task_spec: dict[str, Any] | None = None) -> dict[str, Any]:
    hints = list((task_spec or {}).get("semantic_hints") or SEMANTIC_HINTS)
    lowered = code.lower()
    code_hits = {hint: hint.lower() in lowered or hint.lower().replace("_", "") in lowered.replace("_", "") for hint in hints}
    code_score = sum(1 for ok in code_hits.values() if ok) / max(1, len(hints))

    bbox = bbox_dict(mesh)
    height = max(bbox["zlen"], 1e-9)
    if task_spec and task_spec.get("bbox_mm"):
        target = np.asarray(task_spec["bbox_mm"], dtype=float)
        target = target / max(target[2], 1e-9)
        actual = np.asarray([bbox["xlen"], bbox["ylen"], bbox["zlen"]], dtype=float)
        actual = actual / max(actual[2], 1e-9)
        ratio_score = float(max(0.0, 1.0 - np.mean(np.abs(actual - target) / np.maximum(target, 1e-9))))
        geometry_score = ratio_score
    else:
        width_ratio = bbox["xlen"] / height
        depth_ratio = bbox["ylen"] / height
        chair_ratio_score = float(max(0.0, 1.0 - abs(width_ratio - 0.55) - abs(depth_ratio - 0.60)))

        vertices = np.asarray(mesh.vertices)
        lower = vertices[vertices[:, 2] < bbox["zmin"] + 0.25 * height]
        upper = vertices[vertices[:, 2] > bbox["zmin"] + 0.55 * height]
        lower_radius = 0.0 if len(lower) == 0 else float(np.percentile(np.linalg.norm(lower[:, :2], axis=1), 90) / height)
        upper_height_presence = float(len(upper) > max(20, len(vertices) * 0.08))
        base_spread_score = float(min(1.0, lower_radius / 0.30))
        geometry_score = 0.45 * chair_ratio_score + 0.35 * base_spread_score + 0.20 * upper_height_presence

    functions = len(re.findall(r"^\s*def\s+\w+\s*\(", code, re.MULTILINE))
    assembly_score = min(1.0, functions / 6.0)
    score = 0.35 * code_score + 0.45 * geometry_score + 0.20 * assembly_score
    return {
        "score": float(max(0.0, min(1.0, score))),
        "code_hits": code_hits,
        "code_score": float(code_score),
        "geometry_score": float(geometry_score),
        "function_count": functions,
        "assembly_score": float(assembly_score),
    }


def editability_reward(code: str) -> dict[str, Any]:
    functions = len(re.findall(r"^\s*def\s+\w+\s*\(", code, re.MULTILINE))
    named_values = len(re.findall(r"^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*[-+]?\d", code, re.MULTILINE))
    reusable_returns = len(re.findall(r"^\s*return\s+", code, re.MULTILINE))
    show_object = "show_object" in code or "fixture" in code or "result" in code or "chair" in code
    score = 0.35 * min(1.0, functions / 6.0)
    score += 0.20 * min(1.0, named_values / 8.0)
    score += 0.25 * min(1.0, reusable_returns / max(1, functions))
    score += 0.20 if show_object else 0.0
    return {
        "score": float(max(0.0, min(1.0, score))),
        "function_count": functions,
        "named_numeric_assignments": named_values,
        "return_count": reusable_returns,
        "has_final_object": show_object,
    }


def weighted_reference_score(comparison: dict[str, Any]) -> dict[str, Any]:
    def one(ref: dict[str, Any]) -> float:
        return float(0.25 * ref["bbox"] + 0.35 * ref["chamfer"] + 0.40 * ref["silhouette"]["score"])

    glb_score = one(comparison["glb_reference"])
    ideal_score = one(comparison["ideal_cadquery"]) if "ideal_cadquery" in comparison else glb_score
    return {
        "score": float(0.60 * ideal_score + 0.40 * glb_score),
        "ideal_score": float(ideal_score),
        "glb_score": float(glb_score),
    }


def verifier_markdown(result: dict[str, Any]) -> str:
    reward = result["reward"]
    lines = [
        f"# CadQuery Environment Report: {result['episode_id']} / {result['step_id']}",
        "",
        f"- Total reward: `{reward['total']:.3f}`",
        f"- Build: `{reward['build']:.3f}`",
        f"- Topology: `{reward['topology']:.3f}`",
        f"- Contact/gaps: `{reward.get('contact', 0.0):.3f}`",
        f"- Semantic parts: `{reward['semantic_parts']:.3f}`",
        f"- Reference similarity: `{reward['reference_similarity']:.3f}`",
        f"- Silhouette: `{reward['silhouette']:.3f}`",
        f"- Editability: `{reward['editability']:.3f}`",
        "",
        "## Topology",
        "",
        "```json",
        json.dumps(result["topology"], indent=2),
        "```",
        "",
        "## Notes",
    ]
    for note in result["notes"]:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def evaluate_code(
    code: str,
    episode_id: str,
    step_id: str,
    task_prompt: str = "",
    reference_root: Path = REFERENCE_ROOT,
    reward_mode: str = "full",
    task_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if reward_mode not in {"fast", "full"}:
        raise ValueError(f"reward_mode must be fast or full, got {reward_mode}")
    using_default_reference = reference_root.resolve() == REFERENCE_ROOT.resolve()
    reference_summary = load_reference_summary(reference_root, auto_default=using_default_reference)
    reference_available = bool(reference_summary) and (reference_root / "glb_reference" / "metrics.json").exists()
    episode_dir = RUNS_ROOT / safe_slug(episode_id) / safe_slug(step_id)
    if episode_dir.exists():
        shutil.rmtree(episode_dir)
    episode_dir.mkdir(parents=True, exist_ok=True)
    (episode_dir / "candidate.py").write_text(code)
    if task_prompt:
        (episode_dir / "task_prompt.txt").write_text(task_prompt)
    if task_spec:
        (episode_dir / "task_spec.json").write_text(json.dumps(task_spec, indent=2))

    run = run_cadquery(code, episode_dir, "candidate")
    if not run["ok"]:
        error_detail = concise_error(run["stdout"], run["stderr"])
        notes = ["CadQuery code did not execute or did not export an STL."]
        if error_detail:
            notes.append(f"Build error: {error_detail}")
        result = {
            "episode_id": episode_id,
            "step_id": step_id,
            "ok": False,
            "artifacts_dir": str(episode_dir),
            "error": "CadQuery execution failed.",
            "stdout": run["stdout"],
            "stderr": run["stderr"],
            "elapsed_ms": run["elapsed_ms"],
            "reward": {
                "total": -1.0,
                "build": 0.0,
                "topology": 0.0,
                "semantic_parts": 0.0,
                "reference_similarity": 0.0,
                "silhouette": 0.0,
                "editability": 0.0,
                "efficiency": 0.0,
            },
            "notes": notes,
        }
        (episode_dir / "reward.json").write_text(json.dumps(result, indent=2))
        (episode_dir / "verifier_report.md").write_text(verifier_markdown({**result, "topology": {}}))
        return result

    stl_path = Path(run["output"]["stl_path"])
    mesh = mesh_from_file(stl_path)
    normalized = normalize_mesh(mesh)
    normalized_stl = episode_dir / "candidate_normalized.stl"
    normalized.export(normalized_stl)
    masks = save_silhouettes(normalized, episode_dir / "masks") if reward_mode == "full" else {}
    renders = save_color_renders(normalized, episode_dir / "renders") if reward_mode == "full" else {}

    topology = topology_metrics(normalized)
    topo_reward = topology_reward(topology)
    contact = contact_metrics(normalized)
    semantic = semantic_reward(code, normalized, task_spec)
    editability = editability_reward(code)
    if reference_available:
        comparison = compare_to_references(
            normalized,
            reference_root,
            mode=reward_mode,
            candidate_silhouettes=masks if reward_mode == "full" else None,
        )
        reference = weighted_reference_score(comparison)
        if "ideal_cadquery" in comparison:
            silhouette = {
                "score": float(
                    0.60 * comparison["ideal_cadquery"]["silhouette"]["score"]
                    + 0.40 * comparison["glb_reference"]["silhouette"]["score"]
                ),
                "ideal": comparison["ideal_cadquery"]["silhouette"],
                "glb": comparison["glb_reference"]["silhouette"],
            }
        else:
            silhouette = {
                "score": float(comparison["glb_reference"]["silhouette"]["score"]),
                "glb": comparison["glb_reference"]["silhouette"],
            }
    else:
        comparison = {}
        reference = {"score": 0.50, "ideal_score": 0.50, "glb_score": 0.50, "reference_available": False}
        silhouette = {"score": 0.50, "reference_available": False, "per_view": {}}
    build = 1.0
    efficiency = 1.0
    if reward_mode == "fast":
        # Fast mode is for dense intermediate RL feedback. Avoid over-weighting
        # bbox-only similarity because blocky impostors can game that signal.
        total = (
            0.22 * build
            + 0.17 * topo_reward["score"]
            + 0.12 * contact["score"]
            + 0.25 * semantic["score"]
            + 0.10 * reference["score"]
            + 0.10 * editability["score"]
            + 0.04 * efficiency
        )
    else:
        total = (
            0.18 * build
            + 0.17 * topo_reward["score"]
            + 0.10 * contact["score"]
            + 0.15 * semantic["score"]
            + 0.15 * reference["score"]
            + 0.10 * silhouette["score"]
            + 0.10 * editability["score"]
            + 0.05 * efficiency
        )
    notes = []
    if topology["components"] > 120:
        notes.append(f"Candidate has {topology['components']} mesh components; acceptable for assemblies only if the parts are intentional.")
    if not topology["watertight"]:
        notes.append("Candidate mesh is not fully watertight; this is tolerated for chair assemblies but should improve for monolithic parts.")
    if contact["large_gap_components"] > 0:
        notes.append(f"Candidate has {contact['large_gap_components']} significant separated components; smaller assembly gaps are okay, large gaps reduce contact reward.")
    if semantic["score"] < 0.45:
        target_name = task_spec.get("id", "target object") if task_spec else "Markus-chair"
        notes.append(f"Candidate is weak on {target_name} semantic hints; add/organize recognizable subassemblies in code.")
    if reference_available and reference["score"] < 0.35:
        notes.append("Candidate is still far from the ideal CadQuery/reference GLB shape.")
    if not reference_available:
        notes.append("No task-specific GLB reference is available yet; reward uses build, topology, contact, task semantics, bbox profile, and editability.")

    result = {
        "episode_id": episode_id,
        "step_id": step_id,
        "ok": True,
        "reward_mode": reward_mode,
        "artifacts_dir": str(episode_dir),
        "candidate_stl": str(stl_path),
        "candidate_normalized_stl": str(normalized_stl),
        "renders": renders,
        "masks": masks,
        "elapsed_ms": run["elapsed_ms"],
        "bbox": bbox_dict(mesh),
        "normalized_bbox": bbox_dict(normalized),
        "topology": topology,
        "contact": contact,
        "semantic_parts": semantic,
        "editability": editability,
        "reference_comparison": comparison,
        "reference_similarity": reference,
        "silhouette": silhouette,
        "reward": {
            "total": float(max(-1.0, min(1.0, total))),
            "build": build,
            "topology": topo_reward["score"],
            "contact": contact["score"],
            "semantic_parts": semantic["score"],
            "reference_similarity": reference["score"],
            "silhouette": silhouette["score"],
            "editability": editability["score"],
            "efficiency": efficiency,
        },
        "notes": notes or ["Candidate built and scored successfully."],
    }
    (episode_dir / "reward.json").write_text(json.dumps(result, indent=2))
    (episode_dir / "verifier_report.md").write_text(verifier_markdown(result))
    return result


def smoke(episodes: int, reward_mode: str = "full") -> dict[str, Any]:
    load_reference_summary()
    ideal_code = read_code(DEFAULT_IDEAL_CODE)
    simple_code = "\n".join(
        [
            "import cadquery as cq",
            "seat = cq.Workplane('XY').box(520, 480, 70).translate((0, 0, 450))",
            "back = cq.Workplane('XY').box(440, 45, 720).translate((0, -235, 760))",
            "column = cq.Workplane('XY').cylinder(360, 28).translate((0, 0, 210))",
            "base = cq.Workplane('XY').cylinder(55, 55).translate((0, 0, 55))",
            "fixture = seat.union(back).union(column).union(base).clean()",
        ]
    )
    results = []
    for i in range(max(1, episodes)):
        code = ideal_code if i == 0 else simple_code
        step = "ideal_reference" if i == 0 else f"simple_candidate_{i}"
        results.append(evaluate_code(code, "smoke", step, "Smoke-test CadQuery Markus chair environment.", reward_mode=reward_mode))
    summary = {
        "episodes": len(results),
        "ok": all(item["ok"] for item in results),
        "best_reward": max(item["reward"]["total"] for item in results),
        "mean_reward": float(np.mean([item["reward"]["total"] for item in results])),
        "results": [
            {
                "step_id": item["step_id"],
                "ok": item["ok"],
                "reward": item["reward"],
                "artifacts_dir": item["artifacts_dir"],
            }
            for item in results
        ],
    }
    (RUNS_ROOT / "smoke_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="CadQuery CADForge reference preprocessing and reward environment.")
    sub = parser.add_subparsers(dest="command", required=True)

    prep = sub.add_parser("preprocess-reference")
    prep.add_argument("--glb", default=str(DEFAULT_GLB))
    prep.add_argument("--ideal-code", default=str(DEFAULT_IDEAL_CODE))
    prep.add_argument("--out-root", default=str(REFERENCE_ROOT))

    eval_parser = sub.add_parser("evaluate")
    eval_parser.add_argument("--code-file")
    eval_parser.add_argument("--episode-id", default="manual")
    eval_parser.add_argument("--step-id", default="step-0")
    eval_parser.add_argument("--task-prompt", default="")
    eval_parser.add_argument("--reward-mode", choices=["fast", "full"], default="full")
    eval_parser.add_argument("--task-spec", default="")
    eval_parser.add_argument("--reference-root", default=str(REFERENCE_ROOT))

    smoke_parser = sub.add_parser("smoke")
    smoke_parser.add_argument("--episodes", type=int, default=2)
    smoke_parser.add_argument("--reward-mode", choices=["fast", "full"], default="full")

    args = parser.parse_args()
    if args.command == "preprocess-reference":
        ideal_code = Path(args.ideal_code) if args.ideal_code else None
        result = preprocess_reference(Path(args.glb), ideal_code, Path(args.out_root))
    elif args.command == "evaluate":
        if args.code_file:
            code = read_code(Path(args.code_file))
        else:
            payload = json.loads(sys.stdin.read() or "{}")
            code = extract_code(str(payload.get("code", "")))
        result = evaluate_code(
            code,
            args.episode_id,
            args.step_id,
            args.task_prompt,
            reference_root=Path(args.reference_root),
            reward_mode=args.reward_mode,
            task_spec=read_task_spec(args.task_spec),
        )
    elif args.command == "smoke":
        result = smoke(args.episodes, reward_mode=args.reward_mode)
    else:
        raise AssertionError(args.command)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
