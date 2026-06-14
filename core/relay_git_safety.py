"""Relay Git Write Safety — runtime guard for git write operations.

Checks environment gates before allowing git commit/tag/push/deploy.
Default-deny: missing or non-"YES" env var = blocked.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class GitOp(Enum):
    COMMIT = "commit"
    TAG = "tag"
    PUSH = "push"
    DEPLOY = "deploy"


_ENV_MAP = {
    GitOp.COMMIT: "ALLOW_GIT_COMMIT",
    GitOp.TAG: "ALLOW_GIT_TAG",
    GitOp.PUSH: "ALLOW_GIT_PUSH",
    GitOp.DEPLOY: "ALLOW_GIT_DEPLOY",
}


@dataclass
class SafetyCheckResult:
    allowed: bool
    op: GitOp
    env_var: str
    env_value: str | None
    reason: str


def check_git_op_allowed(op: GitOp) -> SafetyCheckResult:
    """Check if a git write operation is allowed by environment gate."""
    env_var = _ENV_MAP[op]
    env_value = os.environ.get(env_var)
    allowed = env_value == "YES"
    if allowed:
        reason = f"{env_var}=YES, operation permitted"
    elif env_value is None:
        reason = f"{env_var} not set, operation DENIED (default-deny)"
    else:
        reason = f"{env_var}={env_value!r}, operation DENIED (only YES permits)"
    return SafetyCheckResult(
        allowed=allowed, op=op, env_var=env_var,
        env_value=env_value, reason=reason,
    )


def guard_git_command(argv: Sequence[str]) -> SafetyCheckResult:
    """Analyze a command argv and return safety check for the git operation it would perform.

    Returns SafetyCheckResult. If the command is not a git write op,
    returns allowed=True with reason indicating no guard needed.
    """
    if not argv:
        return SafetyCheckResult(True, GitOp.COMMIT, "", None, "empty command, no guard needed")

    cmd = " ".join(argv).lower()

    if "git push" in cmd or "push --tags" in cmd:
        return check_git_op_allowed(GitOp.PUSH)
    if "git tag" in cmd and "-d" not in cmd and "-l" not in cmd and "--list" not in cmd:
        return check_git_op_allowed(GitOp.TAG)
    if "git commit" in cmd:
        return check_git_op_allowed(GitOp.COMMIT)
    if "gh release" in cmd:
        return check_git_op_allowed(GitOp.DEPLOY)

    return SafetyCheckResult(True, GitOp.COMMIT, "", None, "not a guarded git write operation")


def enforce_git_safety(argv: Sequence[str]) -> None:
    """Raise RuntimeError if the command violates git write safety policy."""
    result = guard_git_command(argv)
    if not result.allowed:
        raise RuntimeError(
            f"RELAY GIT SAFETY BLOCKED: {result.reason}. "
            f"Command: {' '.join(argv)}"
        )
