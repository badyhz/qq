from dataclasses import dataclass

from core.offline_shadow_parameter_set import OfflineShadowParameterSet
from core.offline_shadow_safety_policy import OfflineShadowSafetyPolicy
from core.offline_shadow_symbol import OfflineShadowSymbol
from core.offline_shadow_timeframe import OfflineShadowTimeframe
from core.offline_shadow_window import OfflineShadowWindow


@dataclass(frozen=True)
class OfflineShadowExperiment:
    experiment_id: str
    symbol: OfflineShadowSymbol
    timeframe: OfflineShadowTimeframe
    window: OfflineShadowWindow
    parameter_set: OfflineShadowParameterSet
    safety_policy: OfflineShadowSafetyPolicy
