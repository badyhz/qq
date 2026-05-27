from __future__ import annotations

import pytest

from core.human_review_forbidden_approval import (
    VALID_CATEGORIES,
    HumanReviewForbiddenApproval,
    build_forbidden_approval,
)


class TestHumanReviewForbiddenApproval:
    def test_build_live_trading(self) -> None:
        fa = build_forbidden_approval("LIVE_TRADING", "no live")
        assert fa.category == "LIVE_TRADING"
        assert fa.requires_human_override is True

    def test_build_credential_access(self) -> None:
        fa = build_forbidden_approval("CREDENTIAL_ACCESS", "no creds")
        assert fa.category == "CREDENTIAL_ACCESS"

    def test_build_exchange_connection(self) -> None:
        fa = build_forbidden_approval("EXCHANGE_CONNECTION", "no conn")
        assert fa.category == "EXCHANGE_CONNECTION"

    def test_build_planner_integration(self) -> None:
        fa = build_forbidden_approval("PLANNER_INTEGRATION", "no planner")
        assert fa.category == "PLANNER_INTEGRATION"

    def test_frozen(self) -> None:
        fa = build_forbidden_approval("LIVE_TRADING", "x")
        with pytest.raises(AttributeError):
            fa.category = "Y"  # type: ignore[misc]

    def test_requires_human_override_default(self) -> None:
        fa = build_forbidden_approval("LIVE_TRADING", "d")
        assert fa.requires_human_override is True

    def test_requires_human_override_false(self) -> None:
        fa = build_forbidden_approval("LIVE_TRADING", "d", requires_human_override=False)
        assert fa.requires_human_override is False

    def test_invalid_category(self) -> None:
        with pytest.raises(ValueError, match="Invalid category"):
            build_forbidden_approval("BOGUS", "x")

    def test_valid_categories_frozen(self) -> None:
        assert isinstance(VALID_CATEGORIES, frozenset)
        assert len(VALID_CATEGORIES) == 4
