from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import EnvironmentMetadata

from cadquery_env import APP_ROOT, evaluate_code, preprocess_reference, read_task_spec

from .openenv_models import CadForgeAction, CadForgeObservation, CadForgeState


DEFAULT_TASK_ID = "four_leg_chair_700n"

CADQUERY_CONSTRAINTS = [
    "Return a complete Python file, not markdown.",
    "Use import cadquery as cq; the runner also provides cq, exporters, math, Assembly, and Color.",
    "Assign the final exportable object to fixture, result, model, solid, body, part, or call show_object(obj).",
    "Do not use file IO, networking, subprocesses, eval, exec, unsupported imports, or CQ-editor-only helpers.",
    "Prefer named dimensions, helper functions, connected parts, and simple robust CadQuery operations.",
]


def seed_code_for(task_id: str) -> str:
    if task_id == "four_leg_chair_700n":
        return "\n".join(
            [
                "import cadquery as cq",
                "",
                "seat_width = 520",
                "seat_depth = 470",
                "seat_thickness = 55",
                "leg_height = 420",
                "",
                "seat = cq.Workplane('XY').box(seat_width, seat_depth, seat_thickness).translate((0, 0, leg_height))",
                "# Weak seed: only one central support and a floating backrest; repair into a real chair.",
                "support = cq.Workplane('XY').cylinder(leg_height, 35).translate((0, 0, leg_height / 2))",
                "backrest = cq.Workplane('XY').box(440, 45, 520).translate((0, -330, 700))",
                "fixture = seat.union(support).union(backrest).clean()",
            ]
        )
    return "\n".join(
        [
            "import cadquery as cq",
            "",
            "# Generic weak seed: a buildable blocky placeholder that needs task-specific repair.",
            "base = cq.Workplane('XY').box(90, 50, 14).translate((0, 0, 7))",
            "boss = cq.Workplane('XY').cylinder(40, 18).translate((35, 0, 34))",
            "fixture = base.union(boss).clean()",
        ]
    )


class CadForgeCadQueryEnvironment(Environment[CadForgeAction, CadForgeObservation, CadForgeState]):
    """OpenEnv wrapper around the CADForge CadQuery compile/render/reward loop."""

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        self._state = CadForgeState(episode_id=str(uuid4()), step_count=0)
        self._done = False

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        task_id: str | None = None,
        task_brief: str | None = None,
        **_: object,
    ) -> CadForgeObservation:
        selected_task_id = task_id or DEFAULT_TASK_ID
        task_spec = self._task_spec(selected_task_id)
        prompt = task_brief or task_spec.get("prompt", "")
        self._state = CadForgeState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_id=selected_task_id,
            task_brief=prompt,
            current_code=seed_code_for(selected_task_id),
        )
        self._done = False
        return self._observation(
            reward=0.0,
            notes=["Ready. Submit complete CadQuery code as the action.code field."],
        )

    def step(self, action: CadForgeAction, timeout_s: float | None = None, **_: object) -> CadForgeObservation:  # type: ignore[override]
        task_id = action.task_id or self._state.task_id or DEFAULT_TASK_ID
        task_spec = self._task_spec(task_id)
        task_prompt = action.task_prompt or task_spec.get("prompt", self._state.task_brief)
        self._state.task_id = task_id
        self._state.task_brief = task_prompt
        self._state.step_count += 1

        reference_root = self._reference_root(task_id)
        result = evaluate_code(
            action.code,
            self._state.episode_id or str(uuid4()),
            f"step-{self._state.step_count}",
            task_prompt,
            reference_root=reference_root,
            reward_mode=action.reward_mode,
            task_spec=task_spec,
        )

        reward_json = result.get("reward", {})
        reward = float(reward_json.get("total", -1.0))
        self._state.current_code = action.code
        self._state.last_reward = reward_json
        self._state.trace.append(
            {
                "step": self._state.step_count,
                "task_id": task_id,
                "reward_mode": action.reward_mode,
                "reward": reward_json,
                "ok": result.get("ok", False),
                "notes": result.get("notes", []),
                "artifacts_dir": result.get("artifacts_dir"),
            }
        )
        self._done = reward >= 0.92 or self._state.step_count >= 12
        return self._observation(
            reward=reward,
            notes=result.get("notes", []),
            reward_json=reward_json,
            artifacts_dir=result.get("artifacts_dir"),
            renders=result.get("renders", {}),
            done=self._done,
        )

    @property
    def state(self) -> CadForgeState:
        return self._state

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="cadforge_cadquery",
            description=(
                "Agentic CadQuery repair environment. Agents submit complete Python CadQuery "
                "files, the environment executes them in a constrained runner, exports STL, "
                "scores build/topology/contact/task semantics/reference similarity/editability, "
                "and returns dense reward for SFT/GRPO loops."
            ),
            version="0.1.0",
            author="Sanjayprasad H S",
        )

    def _task_spec(self, task_id: str) -> dict:
        try:
            return read_task_spec(task_id) or {"id": task_id, "prompt": ""}
        except FileNotFoundError:
            return {"id": task_id, "prompt": self._state.task_brief}

    def _reference_root(self, task_id: str) -> Path:
        packaged_ref_root = APP_ROOT / "data" / "reference-metrics" / task_id
        if (packaged_ref_root / "reference_summary.json").exists():
            return packaged_ref_root

        ref_root = APP_ROOT / "runs" / "cadquery-task-references" / task_id
        if (ref_root / "reference_summary.json").exists():
            return ref_root

        glb_path = APP_ROOT / "data" / "generated-assets" / task_id / "reference.glb"
        if glb_path.exists():
            preprocess_reference(glb_path, ideal_code_path=None, out_root=ref_root)
        return ref_root

    def _observation(
        self,
        reward: float,
        notes: list[str],
        reward_json: dict | None = None,
        artifacts_dir: str | None = None,
        renders: dict | None = None,
        done: bool | None = None,
    ) -> CadForgeObservation:
        return CadForgeObservation(
            task_brief=self._state.task_brief,
            task_id=self._state.task_id,
            constraints=CADQUERY_CONSTRAINTS,
            current_code=self._state.current_code,
            reward_json=reward_json or self._state.last_reward,
            verifier_notes=notes,
            artifacts_dir=artifacts_dir,
            renders=renders or {},
            trace=self._state.trace,
            done=self._done if done is None else done,
            reward=reward,
        )
