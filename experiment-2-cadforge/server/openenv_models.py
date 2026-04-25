from __future__ import annotations

from typing import Any

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


class CadForgeAction(Action):
    """A complete CadQuery repair candidate to compile and score."""

    code: str = Field(..., min_length=1, description="Complete executable Python CadQuery file")
    task_id: str = Field(default="four_leg_chair_700n", description="CADForge task id from data/cad_tasks.json")
    reward_mode: str = Field(default="fast", pattern="^(fast|full)$", description="Use fast dense reward or full report reward")
    task_prompt: str | None = Field(default=None, description="Optional task prompt override")


class CadForgeObservation(Observation):
    """Verifier feedback returned after compiling and scoring CadQuery code."""

    task_brief: str = Field(default="", description="Natural language design brief")
    task_id: str = Field(default="four_leg_chair_700n", description="Active CADForge task id")
    constraints: list[str] = Field(default_factory=list, description="CadQuery/runtime constraints the agent must obey")
    current_code: str = Field(default="", description="Starting or most recently submitted CadQuery code")
    reward_json: dict[str, Any] = Field(default_factory=dict, description="Latest scalar reward components")
    verifier_notes: list[str] = Field(default_factory=list, description="Human-readable verifier notes")
    artifacts_dir: str | None = Field(default=None, description="Directory containing candidate code, STL, reward JSON, and optional renders")
    renders: dict[str, str] = Field(default_factory=dict, description="Full-mode render paths by view")
    trace: list[dict[str, Any]] = Field(default_factory=list, description="Per-step action/reward trace")


class CadForgeState(State):
    """Internal CadQuery repair state."""

    task_id: str = "four_leg_chair_700n"
    task_brief: str = ""
    current_code: str = ""
    last_reward: dict[str, Any] = Field(default_factory=dict)
    trace: list[dict[str, Any]] = Field(default_factory=list)


# Backward-compatible aliases for older local imports.
MechForgeAction = CadForgeAction
MechForgeObservation = CadForgeObservation
MechForgeState = CadForgeState
