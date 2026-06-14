"""Tests for relay git write safety guard and scanner."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from core.relay_git_safety import (
    GitOp,
    SafetyCheckResult,
    check_git_op_allowed,
    enforce_git_safety,
    guard_git_command,
)


class TestCheckGitOpAllowed:
    """Default-deny: no env var or wrong value = blocked."""

    def test_commit_denied_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            r = check_git_op_allowed(GitOp.COMMIT)
        assert not r.allowed
        assert "DENIED" in r.reason

    def test_tag_denied_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            r = check_git_op_allowed(GitOp.TAG)
        assert not r.allowed

    def test_push_denied_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            r = check_git_op_allowed(GitOp.PUSH)
        assert not r.allowed

    def test_deploy_denied_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            r = check_git_op_allowed(GitOp.DEPLOY)
        assert not r.allowed

    def test_commit_allowed_when_yes(self):
        with mock.patch.dict(os.environ, {"ALLOW_GIT_COMMIT": "YES"}):
            r = check_git_op_allowed(GitOp.COMMIT)
        assert r.allowed

    def test_commit_denied_when_no(self):
        with mock.patch.dict(os.environ, {"ALLOW_GIT_COMMIT": "NO"}):
            r = check_git_op_allowed(GitOp.COMMIT)
        assert not r.allowed

    def test_tag_allowed_when_yes(self):
        with mock.patch.dict(os.environ, {"ALLOW_GIT_TAG": "YES"}):
            r = check_git_op_allowed(GitOp.TAG)
        assert r.allowed

    def test_push_allowed_when_yes(self):
        with mock.patch.dict(os.environ, {"ALLOW_GIT_PUSH": "YES"}):
            r = check_git_op_allowed(GitOp.PUSH)
        assert r.allowed


class TestGuardGitCommand:
    """guard_git_command parses argv and returns correct SafetyCheckResult."""

    def test_empty_command(self):
        r = guard_git_command([])
        assert r.allowed

    def test_git_push_detected(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            r = guard_git_command(["git", "push", "origin", "main"])
        assert not r.allowed
        assert r.op == GitOp.PUSH

    def test_git_commit_detected(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            r = guard_git_command(["git", "commit", "-m", "test"])
        assert not r.allowed
        assert r.op == GitOp.COMMIT

    def test_git_tag_create_detected(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            r = guard_git_command(["git", "tag", "v1.0"])
        assert not r.allowed
        assert r.op == GitOp.TAG

    def test_git_tag_list_not_blocked(self):
        """git tag -l (list) should not be blocked."""
        r = guard_git_command(["git", "tag", "-l"])
        assert r.allowed

    def test_git_tag_delete_not_blocked(self):
        """git tag -d (delete local) should not be blocked."""
        r = guard_git_command(["git", "tag", "-d", "old-tag"])
        assert r.allowed

    def test_non_git_command_allowed(self):
        r = guard_git_command(["python3", "-m", "pytest"])
        assert r.allowed

    def test_gh_release_detected(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            r = guard_git_command(["gh", "release", "create", "v1.0"])
        assert not r.allowed
        assert r.op == GitOp.DEPLOY


class TestEnforceGitSafety:
    """enforce_git_safety raises on violation, silent on pass."""

    def test_raises_on_blocked_commit(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="BLOCKED"):
                enforce_git_safety(["git", "commit", "-m", "test"])

    def test_no_raise_on_non_git_command(self):
        enforce_git_safety(["python3", "main.py"])

    def test_no_raise_when_authorized(self):
        with mock.patch.dict(os.environ, {"ALLOW_GIT_COMMIT": "YES"}):
            enforce_git_safety(["git", "commit", "-m", "test"])


class TestHistoricalAuthorizationNotReusable:
    """Previous round authorization must not carry over."""

    def test_env_not_persisted_across_calls(self):
        """Simulate: round 1 authorizes, round 2 has no env."""
        with mock.patch.dict(os.environ, {"ALLOW_GIT_COMMIT": "YES"}):
            r1 = check_git_op_allowed(GitOp.COMMIT)
        assert r1.allowed

        # Round 2: env cleared
        with mock.patch.dict(os.environ, {}, clear=True):
            r2 = check_git_op_allowed(GitOp.COMMIT)
        assert not r2.allowed


class TestScanProject:
    """Test the static scanner logic directly."""

    def test_scanner_finds_dangerous_pattern(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text('subprocess.run("git push origin main")\n')
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
        from check_relay_git_write_safety import scan_file
        findings = scan_file(f)
        assert len(findings) > 0
        assert any("git push" in name for _, _, name, _ in findings)

    def test_scanner_ignores_safe_code(self, tmp_path):
        f = tmp_path / "safe.py"
        f.write_text('print("hello world")\n')
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
        from check_relay_git_write_safety import scan_file
        findings = scan_file(f)
        assert len(findings) == 0

    def test_scanner_detects_git_push_in_json(self, tmp_path):
        """settings.local.json with git push must be flagged."""
        f = tmp_path / "settings.local.json"
        f.write_text('{"permissions": {"allow": ["Bash(git push *)"]}}\n')
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
        from check_relay_git_write_safety import scan_file
        findings = scan_file(f)
        assert len(findings) > 0
        assert any("git push" in name for _, _, name, _ in findings)

    def test_scanner_marks_comment_as_advisory(self, tmp_path):
        """Comment lines with dangerous patterns should be flagged as advisory."""
        f = tmp_path / "example.py"
        f.write_text('# Call this BEFORE creating any git tag\nprint("hi")\n')
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
        from check_relay_git_write_safety import scan_file
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0][3] is True  # is_comment = True

    def test_scanner_marks_code_as_must_fix(self, tmp_path):
        """Code lines with dangerous patterns must not be marked as comments."""
        f = tmp_path / "dangerous.py"
        f.write_text('os.system("git tag v1.0")\n')
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
        from check_relay_git_write_safety import scan_file
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0][3] is False  # is_comment = False

    def test_scanner_skips_commit_recorder(self, tmp_path):
        """commit_recorder.sh is in SELF_REFERENCE_NAMES and should be skipped."""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
        from check_relay_git_write_safety import should_skip_file
        assert should_skip_file(Path("scripts/commit_recorder.sh"))

    def test_claude_dir_not_excluded(self):
        """Verify .claude is no longer in EXCLUDE_DIRS."""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
        from check_relay_git_write_safety import EXCLUDE_DIRS
        assert ".claude" not in EXCLUDE_DIRS


class TestCommitRecorderGuard:
    """commit_recorder.sh must require ALLOW_GIT_COMMIT=YES."""

    def test_recorder_blocked_without_env(self, tmp_path):
        """Script exits 1 when ALLOW_GIT_COMMIT is unset."""
        script = Path(__file__).resolve().parent.parent.parent / "scripts" / "commit_recorder.sh"
        if not script.exists():
            pytest.skip("commit_recorder.sh not found")
        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True, text=True,
            env={**os.environ, "ALLOW_GIT_COMMIT": ""},
            timeout=10,
        )
        assert result.returncode != 0
        assert "BLOCKED" in result.stdout + result.stderr

    def test_recorder_blocked_with_wrong_value(self, tmp_path):
        """Script exits 1 when ALLOW_GIT_COMMIT=NO."""
        script = Path(__file__).resolve().parent.parent.parent / "scripts" / "commit_recorder.sh"
        if not script.exists():
            pytest.skip("commit_recorder.sh not found")
        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True, text=True,
            env={**os.environ, "ALLOW_GIT_COMMIT": "NO"},
            timeout=10,
        )
        assert result.returncode != 0
        assert "BLOCKED" in result.stdout + result.stderr
