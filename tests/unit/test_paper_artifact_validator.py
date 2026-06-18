"""Tests for artifact validator module."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from core.paper_trading.artifact_validator import (
    ValidationIssue, validate_artifacts, validate_artifact, has_errors,
)


class TestValidateJson:
    def test_valid_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"test": True}, f)
            path = f.name
        try:
            issues = validate_artifact(path)
            assert len(issues) == 0
        finally:
            os.unlink(path)

    def test_invalid_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("not json{{{")
            path = f.name
        try:
            issues = validate_artifact(path)
            assert len(issues) == 1
            assert issues[0].level == "ERROR"
        finally:
            os.unlink(path)

    def test_empty_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            issues = validate_artifact(path)
            assert any(i.level == "ERROR" for i in issues)
        finally:
            os.unlink(path)


class TestValidateJsonl:
    def test_valid_jsonl(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
            f.write(json.dumps({"a": 1}) + "\n")
            f.write(json.dumps({"b": 2}) + "\n")
            path = f.name
        try:
            issues = validate_artifact(path)
            assert len(issues) == 0
        finally:
            os.unlink(path)

    def test_corrupted_jsonl(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
            f.write(json.dumps({"a": 1}) + "\n")
            f.write("not json\n")
            path = f.name
        try:
            issues = validate_artifact(path)
            assert len(issues) == 1
            assert "Corrupted line" in issues[0].message
        finally:
            os.unlink(path)


class TestValidateMarkdown:
    def test_valid_md(self):
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
            f.write("# Report\n\nSafety: PAPER_ONLY\n")
            path = f.name
        try:
            issues = validate_artifact(path)
            assert len(issues) == 0
        finally:
            os.unlink(path)

    def test_empty_md(self):
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
            path = f.name
        try:
            issues = validate_artifact(path)
            assert any(i.level == "ERROR" for i in issues)
        finally:
            os.unlink(path)


class TestValidateHtml:
    def test_valid_html(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
            f.write("<html><body>Paper Trading</body></html>")
            path = f.name
        try:
            issues = validate_artifact(path)
            assert len(issues) == 0
        finally:
            os.unlink(path)

    def test_external_http(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
            f.write('<html><link rel="stylesheet" href="https://cdn.example.com/style.css"></html>')
            path = f.name
        try:
            issues = validate_artifact(path)
            assert any("external" in i.message.lower() or "stylesheet" in i.message.lower() for i in issues)
        finally:
            os.unlink(path)

    def test_script_src(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
            f.write('<html><script src="https://evil.com/hack.js"></script></html>')
            path = f.name
        try:
            issues = validate_artifact(path)
            assert any("script" in i.message.lower() for i in issues)
        finally:
            os.unlink(path)

    def test_empty_html(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
            path = f.name
        try:
            issues = validate_artifact(path)
            assert any(i.level == "ERROR" for i in issues)
        finally:
            os.unlink(path)


class TestMissingArtifact:
    def test_missing_file(self):
        issues = validate_artifact("/tmp/nonexistent_paper_artifact.json")
        assert len(issues) == 1
        assert issues[0].level == "ERROR"


class TestHasErrors:
    def test_no_errors(self):
        issues = [ValidationIssue("f", "WARNING", "warn")]
        assert has_errors(issues) is False

    def test_has_error(self):
        issues = [ValidationIssue("f", "ERROR", "bad")]
        assert has_errors(issues) is True


class TestValidateArtifactsDir:
    def test_nonexistent_dir(self):
        issues = validate_artifacts("/tmp/nonexistent_paper_dir")
        assert len(issues) == 1
        assert issues[0].level == "ERROR"
