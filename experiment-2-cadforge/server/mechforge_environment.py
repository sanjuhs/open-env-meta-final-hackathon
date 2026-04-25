from __future__ import annotations

from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import EnvironmentMetadata

from mechforge.models import Design, ToolAction
from mechforge.tools import apply_action

from .openenv_models import MechForgeAction, MechForgeObservation, MechForgeState


AVAILABLE_TOOLS = [
    "create_design_family",
    "set_material",
    "set_envelope",
    "set_load",
    "add_mount_hole",
    "add_rib",
    "add_lightening_hole",
    "run_fea",
    "commit_design",
]


DEFAULT_TASK = (
    "Design a lightweight 6061 aluminum cantilever motor-mount bracket. "
    "It is fixed on the left face by two M5 bolts and must carry 120 N downward "
    "at the tip/load boss around 90 mm from the fixed edge. Keep mass low while "
    "maintaining safety factor above 2.0 and minimizing deflection."
)


class MechForgeEnvironment(Environment[MechForgeAction, MechForgeObservation, MechForgeState]):
    """OpenEnv-compatible MechForge 3D engineering design environment."""

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        self._state = MechForgeState(episode_id=str(uuid4()), step_count=0, task_brief=DEFAULT_TASK)
        self._design: Design | None = None
        self._done = False

    def reset(self, seed: int | None = None, episode_id: str | None = None, task_brief: str | None = None, **_: object) -> MechForgeObservation:
        self._state = MechForgeState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_brief=task_brief or DEFAULT_TASK,
        )
        self._design = None
        self._done = False
        return self._observation(reward=0.0, last_result={"message": "Ready. Create a design family, set constraints, then run FEA."})

    def step(self, action: MechForgeAction, timeout_s: float | None = None, **_: object) -> MechForgeObservation:  # type: ignore[override]
        if self._done:
            return self._observation(reward=0.0, last_result={"valid": False, "error": "Episode is already done."}, done=True)

        self._state.step_count += 1
        tool_action = ToolAction(tool=action.tool, params=action.params)
        self._design, result = apply_action(self._design, tool_action, self._state.task_brief)

        trace_item = {
            "step": self._state.step_count,
            "action": tool_action.model_dump(),
            "result": result,
        }
        self._state.trace.append(trace_item)
        self._state.design = self._design.model_dump() if self._design else None

        metrics = result.get("simulation", {})
        if metrics:
            self._state.last_metrics = metrics

        reward = self._reward(result)
        if result.get("committed") or self._state.step_count >= 300:
            self._done = True

        return self._observation(reward=reward, last_action=tool_action.model_dump(), last_result=result, done=self._done)

    @property
    def state(self) -> MechForgeState:
        return self._state

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="mechforge_3d",
            description=(
                "Agentic 3D engineering design environment. Agents build parametric "
                "brackets/mounts through tool calls, run Python 3D linear FEA, inspect "
                "stress/deflection feedback, and optimize manufacturable designs."
            ),
            version="0.1.0",
            author="Sanjayprasad H S",
        )

    def _reward(self, result: dict) -> float:
        if not result.get("valid", False):
            return -0.05

        sim = result.get("simulation")
        if not sim:
            return 0.02

        score = float(sim.get("score", 0.0))
        safety_factor = float(sim.get("safety_factor", 0.0))
        mass_g = float(sim.get("mass_g", 999.0))
        penalty = 0.0
        if safety_factor < 2.0:
            penalty += 0.2 * (2.0 - safety_factor)
        if mass_g > 90:
            penalty += 0.01 * ((mass_g - 90) / 10)
        return max(-1.0, min(1.0, score - penalty))

    def _observation(
        self,
        reward: float,
        last_action: dict | None = None,
        last_result: dict | None = None,
        done: bool | None = None,
    ) -> MechForgeObservation:
        warnings: list[str] = []
        if self._state.last_metrics.get("safety_factor", 999) < 2.0:
            warnings.append("Safety factor below target 2.0.")
        if self._state.last_metrics.get("mass_g", 0) > 90:
            warnings.append("Design is heavy for the current benchmark.")

        return MechForgeObservation(
            task_brief=self._state.task_brief,
            available_tools=AVAILABLE_TOOLS,
            design=self._design.model_dump() if self._design else None,
            last_action=last_action,
            last_result=last_result or {},
            metrics=self._state.last_metrics,
            warnings=warnings,
            trace=self._state.trace,
            done=self._done if done is None else done,
            reward=reward,
        )

