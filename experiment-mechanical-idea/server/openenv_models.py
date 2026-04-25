from __future__ import annotations

from typing import Any

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


class MechForgeAction(Action):
    """One agent tool call inside the MechForge environment."""

    tool: str = Field(..., description="Tool name, such as add_rib or run_fea")
    params: dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


class MechForgeObservation(Observation):
    """Observation returned after each MechForge tool call."""

    task_brief: str = Field(default="", description="Natural language design brief")
    available_tools: list[str] = Field(default_factory=list, description="Tools the agent may call")
    design: dict[str, Any] | None = Field(default=None, description="Current parametric design")
    last_action: dict[str, Any] | None = Field(default=None, description="Last tool call")
    last_result: dict[str, Any] = Field(default_factory=dict, description="Result of the last tool call")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Latest simulation metrics")
    warnings: list[str] = Field(default_factory=list, description="Environment warnings")
    trace: list[dict[str, Any]] = Field(default_factory=list, description="Action/result trace")


class MechForgeState(State):
    """Internal MechForge state."""

    task_brief: str = ""
    design: dict[str, Any] | None = None
    last_metrics: dict[str, Any] = Field(default_factory=dict)
    trace: list[dict[str, Any]] = Field(default_factory=list)

