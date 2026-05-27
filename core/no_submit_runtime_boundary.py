from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoSubmitRuntimeBoundary:
    component: str
    blocked: bool
    description: str


RUNTIME_COMPONENTS: tuple[NoSubmitRuntimeBoundary, ...] = (
    NoSubmitRuntimeBoundary(
        component="LiveRunner",
        blocked=True,
        description="LiveRunner must not be instantiated or started",
    ),
    NoSubmitRuntimeBoundary(
        component="ExecutionEngine.run_once",
        blocked=True,
        description="ExecutionEngine.run_once must not be called with live connector",
    ),
    NoSubmitRuntimeBoundary(
        component="preflight_bypass",
        blocked=True,
        description="Preflight checks must not be skipped or overridden",
    ),
)
