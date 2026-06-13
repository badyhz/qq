"""Tests for T45001 — Repo Hygiene Scanner."""
from __future__ import annotations

import json
import pytest

from core.repo_hygiene_scanner import (
    FORBIDDEN_TERMS,
    ALLOWED_CONTEXTS,
    PRE_COMMIT_CHECKS,
    RELEASE_HOLD_REQUIRED_RHS,
    HygieneCheck,
    PreCommitHookConfig,
    build_hygiene_check,
    build_pre_commit_config,
    compute_config_hash,
    render_pre_commit_config_markdown,
    render_hygiene_report_markdown,
)


# --- Build checks ---

def test_build_check():
    c = build_hygiene_check(PRE_COMMIT_CHECKS[0])
    assert c.check_id == "forbidden_terms"
    assert c.severity == "BLOCK"
    assert c.pre_commit_hook_compatible is True


def test_build_all_checks():
    for d in PRE_COMMIT_CHECKS:
        c = build_hygiene_check(d)
        assert c.check_id == d["check_id"]
        assert c.pre_commit_hook_compatible is True


# --- Build config ---

def test_build_config():
    config = build_pre_commit_config()
    assert config.hook_name == "qq-hygiene-check"
    assert config.enabled is True
    assert config.blocking is True
    assert len(config.checks) == len(PRE_COMMIT_CHECKS)


def test_config_checks_tuple():
    config = build_pre_commit_config()
    assert isinstance(config.checks, tuple)


# --- Frozen ---

def test_check_is_frozen():
    c = build_hygiene_check(PRE_COMMIT_CHECKS[0])
    with pytest.raises(AttributeError):
        c.check_id = "x"


def test_config_is_frozen():
    config = build_pre_commit_config()
    with pytest.raises(AttributeError):
        config.hook_name = "x"


# --- to_dict ---

def test_check_to_dict_json():
    c = build_hygiene_check(PRE_COMMIT_CHECKS[0])
    json.dumps(c.to_dict())


def test_config_to_dict_json():
    config = build_pre_commit_config()
    json.dumps(config.to_dict())


# --- Hash ---

def test_hash_deterministic():
    config = build_pre_commit_config()
    h1 = compute_config_hash(config)
    h2 = compute_config_hash(config)
    assert h1 == h2


def test_hash_is_sha256():
    config = build_pre_commit_config()
    h = compute_config_hash(config)
    assert len(h) == 64


# --- Markdown ---

def test_render_config_has_header():
    config = build_pre_commit_config()
    md = render_pre_commit_config_markdown(config)
    assert "# Pre-commit Hook Configuration" in md
    assert "qq-hygiene-check" in md


def test_render_config_has_all_checks():
    config = build_pre_commit_config()
    md = render_pre_commit_config_markdown(config)
    for c in config.checks:
        assert c.check_id in md


def test_render_hygiene_report_has_forbidden_terms():
    md = render_hygiene_report_markdown()
    for t in FORBIDDEN_TERMS:
        assert t in md


def test_render_hygiene_report_has_allowed_contexts():
    md = render_hygiene_report_markdown()
    for c in ALLOWED_CONTEXTS:
        assert c in md


def test_render_hygiene_report_has_yaml():
    md = render_hygiene_report_markdown()
    assert ".pre-commit-config.yaml" in md
    assert "qq-hygiene-check" in md


# --- Constants ---

def test_forbidden_terms_count():
    assert len(FORBIDDEN_TERMS) == 4


def test_allowed_contexts_count():
    assert len(ALLOWED_CONTEXTS) == 5


def test_pre_commit_checks_count():
    assert len(PRE_COMMIT_CHECKS) == 4


def test_all_checks_have_severity():
    for c in PRE_COMMIT_CHECKS:
        assert c["severity"] in ("BLOCK", "WARN")
