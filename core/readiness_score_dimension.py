from __future__ import annotations

from enum import Enum


class ReadinessScoreDimension(Enum):
    """Frozen enum-like score dimension with weight and threshold."""

    TEST_COVERAGE = "TEST_COVERAGE"
    DOCUMENTATION = "DOCUMENTATION"
    SAFETY_BOUNDARY = "SAFETY_BOUNDARY"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"
    DEPENDENCY_RESOLUTION = "DEPENDENCY_RESOLUTION"
    REGRESSION_RISK = "REGRESSION_RISK"

    def weight(self) -> float:
        _weights = {
            "TEST_COVERAGE": 0.25,
            "DOCUMENTATION": 0.15,
            "SAFETY_BOUNDARY": 0.25,
            "HUMAN_APPROVAL": 0.15,
            "DEPENDENCY_RESOLUTION": 0.10,
            "REGRESSION_RISK": 0.10,
        }
        return _weights[self.value]

    def threshold(self) -> float:
        _thresholds = {
            "TEST_COVERAGE": 0.80,
            "DOCUMENTATION": 0.70,
            "SAFETY_BOUNDARY": 1.00,
            "HUMAN_APPROVAL": 1.00,
            "DEPENDENCY_RESOLUTION": 1.00,
            "REGRESSION_RISK": 0.90,
        }
        return _thresholds[self.value]
