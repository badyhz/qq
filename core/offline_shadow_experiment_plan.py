from dataclasses import dataclass

from core.offline_shadow_experiment import OfflineShadowExperiment
from core.offline_shadow_run_config import OfflineShadowRunConfig
from core.offline_shadow_safety_policy import OfflineShadowSafetyPolicy


@dataclass(frozen=True)
class OfflineShadowExperimentPlan:
    plan_id: str
    experiments: tuple[OfflineShadowExperiment, ...]
    run_config: OfflineShadowRunConfig
    safety_policy: OfflineShadowSafetyPolicy
