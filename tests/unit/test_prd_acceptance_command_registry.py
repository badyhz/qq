"""Tests for PRD acceptance command registry."""

from core.prd_acceptance_command_registry import (
    PrdAcceptanceCommand,
    acceptance_command_registry_to_dict,
    acceptance_command_registry_to_markdown,
    build_prd_acceptance_command_registry,
    summarize_acceptance_command_registry,
)

REGISTRY = build_prd_acceptance_command_registry()


def test_registry_has_seven_commands():
    assert len(REGISTRY) == 7


def test_required_commands_present():
    required_ids = {c.command_id for c in REGISTRY if c.required}
    assert required_ids == {
        "prd-control-plane",
        "readonly-glob",
        "runtime-governance-glob",
        "governance-failure-glob",
        "order-manager",
    }


def test_commands_contain_no_heredoc():
    for c in REGISTRY:
        assert "<<" not in c.command, f"{c.command_id} contains heredoc"


def test_commands_contain_no_rm():
    for c in REGISTRY:
        assert "rm " not in c.command, f"{c.command_id} contains rm"


def test_commands_contain_no_curl_wget():
    for c in REGISTRY:
        for bad in ("curl ", "wget "):
            assert bad not in c.command, f"{c.command_id} contains {bad.strip()}"


def test_deterministic_output():
    a = build_prd_acceptance_command_registry()
    b = build_prd_acceptance_command_registry()
    assert a == b
    assert acceptance_command_registry_to_dict(a) == acceptance_command_registry_to_dict(b)


def test_frozen_dataclass():
    c = REGISTRY[0]
    try:
        c.command_id = "x"  # type: ignore[misc]
        assert False, "should be frozen"
    except AttributeError:
        pass


def test_to_dict_roundtrip():
    dicts = acceptance_command_registry_to_dict(REGISTRY)
    assert len(dicts) == 7
    for d in dicts:
        assert "command_id" in d
        assert "command" in d
        assert "purpose" in d
        assert "required" in d
        assert "safe_for_agent" in d


def test_to_markdown():
    md = acceptance_command_registry_to_markdown(REGISTRY)
    assert "| command_id |" in md
    assert "prd-control-plane" in md
    assert "git-status" in md


def test_summarize():
    s = summarize_acceptance_command_registry(REGISTRY)
    assert s["total"] == 7
    assert s["required"] == 5
    assert s["optional"] == 2
    assert s["safe_for_agent"] == 7
    assert len(s["command_ids"]) == 7
