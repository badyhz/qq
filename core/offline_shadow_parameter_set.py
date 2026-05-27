from dataclasses import dataclass


@dataclass(frozen=True)
class OfflineShadowParameterSet:
    param_id: str
    label: str
    entry_threshold: float
    exit_threshold: float
    stop_loss_r: float
    take_profit_r: float
    max_hold_bars: int
    min_sample_quality: float
