from dataclasses import dataclass


@dataclass(frozen=True)
class OfflineShadowWindow:
    window_id: str
    window_type: str  # train / validation / test
    start_index: int
    end_index: int
