"""Tests for runtime governance read-only route recommendation — T852."""

from core.runtime_governance_readonly_route_recommendation import (
    RuntimeGovernanceRouteRecommendation,
    build_readonly_route_recommendations,
    route_recommendations_to_dict,
    route_recommendations_to_markdown,
)


def test_five_recommendations() -> None:
    recs = build_readonly_route_recommendations()
    assert len(recs) == 5


def test_live_execution_not_allowed() -> None:
    recs = build_readonly_route_recommendations()
    live = [r for r in recs if r.work_type == "live execution"]
    assert len(live) == 1
    assert live[0].allowed is False
    assert live[0].risk_level == "critical"


def test_secrets_not_allowed() -> None:
    recs = build_readonly_route_recommendations()
    secrets = [r for r in recs if r.work_type == "secrets management"]
    assert len(secrets) == 1
    assert secrets[0].allowed is False
    assert secrets[0].risk_level == "critical"


def test_deterministic() -> None:
    a = build_readonly_route_recommendations()
    b = build_readonly_route_recommendations()
    assert a == b
    assert a is not b


def test_to_dict_returns_list_of_dicts() -> None:
    recs = build_readonly_route_recommendations()
    dicts = route_recommendations_to_dict(recs)
    assert isinstance(dicts, list)
    assert len(dicts) == 5
    for d in dicts:
        assert isinstance(d, dict)
        assert "work_type" in d
        assert "recommended_route" in d
        assert "allowed" in d
        assert "risk_level" in d
        assert "notes" in d


def test_markdown_contains_work_type() -> None:
    recs = build_readonly_route_recommendations()
    md = route_recommendations_to_markdown(recs)
    for r in recs:
        assert r.work_type in md
