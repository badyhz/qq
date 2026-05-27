from dataclasses import dataclass


@dataclass(frozen=True)
class OfflineShadowRunConfig:
    config_id: str
    symbols: tuple[str, ...]
    timeframes: tuple[str, ...]
    windows: tuple[str, ...]
    param_grid: tuple[str, ...]
    fixture_dir: str
    output_dir: str
