from dataclasses import dataclass


@dataclass(frozen=True)
class OfflineShadowTimeframe:
    label: str
    minutes: int
