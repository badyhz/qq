from dataclasses import dataclass


@dataclass(frozen=True)
class OfflineShadowSafetyPolicy:
    no_live: bool
    no_submit: bool
    no_exchange: bool
    release_hold: str

    def __post_init__(self):
        if self.release_hold != "HOLD":
            raise ValueError(
                f"release_hold must be 'HOLD', got '{self.release_hold}'"
            )
