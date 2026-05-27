from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoSubmitCredentialBoundary:
    pattern: str
    blocked: bool
    description: str


CREDENTIAL_PATTERNS: tuple[NoSubmitCredentialBoundary, ...] = (
    NoSubmitCredentialBoundary(
        pattern="api_key_access",
        blocked=True,
        description="Read, parse, or reference API key values",
    ),
    NoSubmitCredentialBoundary(
        pattern="secret_reading",
        blocked=True,
        description="Read secret tokens from files, env vars, or config",
    ),
    NoSubmitCredentialBoundary(
        pattern="env_var_extraction",
        blocked=True,
        description="Call os.environ or os.getenv for credential-related variables",
    ),
)
