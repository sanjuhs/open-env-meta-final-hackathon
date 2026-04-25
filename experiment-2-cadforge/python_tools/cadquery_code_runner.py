from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import cadquery as cq
from cadquery import exporters


BLOCKED_TOKENS = [
    "__",
    "open(",
    "exec(",
    "eval(",
    "compile(",
    "input(",
    "globals(",
    "getattr(",
    "setattr(",
    "delattr(",
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "shutil",
    "pickle",
    "pathlib",
    "os.",
    "sys.",
]

ALLOWED_IMPORT_LINES = {
    "import cadquery as cq",
    "from cadquery import exporters",
    "import math",
}


def clean_code(code: str) -> str:
    value = code.strip()
    value = re.sub(r"^```(?:python|py)?", "", value, flags=re.IGNORECASE).strip()
    value = re.sub(r"```$", "", value).strip()
    lines = []
    for line in value.splitlines():
        stripped = line.strip()
        if stripped in ALLOWED_IMPORT_LINES:
            continue
        if stripped.startswith("import ") or stripped.startswith("from "):
            raise ValueError(f"Unsupported import line: {stripped}")
        lines.append(line)
    return "\n".join(lines).strip()


def validate_code(code: str) -> None:
    lowered = code.lower()
    for token in BLOCKED_TOKENS:
        if token in lowered:
            raise ValueError(f"Blocked Python token in CadQuery code: {token}")


def exportable_object(namespace: dict[str, Any], captured: list[Any]) -> Any:
    if captured:
        return captured[-1]
    for name in ["fixture", "result", "model", "solid", "body", "part"]:
        if name in namespace:
            return namespace[name]
    raise ValueError("CadQuery code must assign the final object to fixture/result/model/solid/body/part or call show_object(obj).")


def normalize_export_object(obj: Any) -> Any:
    if hasattr(obj, "toCompound"):
        return obj.toCompound()
    return obj


def object_bbox(obj: Any):
    obj = normalize_export_object(obj)
    shape = obj.val() if hasattr(obj, "val") else obj
    return shape.BoundingBox()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run constrained CadQuery code and export STL.")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--name", default="generated_cadquery")
    args = parser.parse_args()

    payload = json.loads(sys.stdin.read() or "{}")
    raw_code = str(payload.get("code", ""))
    code = clean_code(raw_code)
    validate_code(code)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", args.name).strip("_") or "generated_cadquery"
    stl_path = out_dir / f"{safe_name}.stl"

    captured: list[Any] = []

    def show_object(obj: Any, *args: Any, **kwargs: Any) -> None:
        captured.append(obj)

    safe_builtins = {
        "abs": abs,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "pow": pow,
        "range": range,
        "round": round,
        "set": set,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
    }
    namespace: dict[str, Any] = {
        "__builtins__": safe_builtins,
        "cq": cq,
        "Assembly": cq.Assembly,
        "Color": cq.Color,
        "exporters": exporters,
        "math": math,
        "show_object": show_object,
    }
    safe_builtins["locals"] = lambda: namespace
    exec(code, namespace, namespace)
    obj = exportable_object(namespace, captured)
    export_obj = normalize_export_object(obj)
    exporters.export(export_obj, str(stl_path))
    bbox = object_bbox(obj)
    print(
        json.dumps(
            {
                "name": safe_name,
                "stl_path": str(stl_path),
                "bounding_box": {
                    "xlen": bbox.xlen,
                    "ylen": bbox.ylen,
                    "zlen": bbox.zlen,
                    "xmin": bbox.xmin,
                    "xmax": bbox.xmax,
                    "ymin": bbox.ymin,
                    "ymax": bbox.ymax,
                    "zmin": bbox.zmin,
                    "zmax": bbox.zmax,
                },
                "cadquery_features": payload.get("features", []),
                "code": code,
            }
        )
    )


if __name__ == "__main__":
    main()
