"""Credential isolation layer.

Centralized abstraction that manages API keys and secrets
without exposing them. Reads from environment variables only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class CredentialValidationResult:
    """Result of validating all registered adapter credentials."""

    valid: bool
    missing: list[str] = field(default_factory=list)
    available: list[str] = field(default_factory=list)


class MissingCredentialError(Exception):
    """Raised when a required credential is not available."""

    def __init__(self, adapter_id: str, env_var: str) -> None:
        self.adapter_id = adapter_id
        self.env_var = env_var
        super().__init__(
            f"Missing credential for adapter '{adapter_id}' "
            f"(env var: {env_var})"
        )


class CredentialManager:
    """Manages adapter credentials via environment variables.

    This module handles NO real secrets. It's an abstraction layer.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def register_adapter(
        self, adapter_id: str, env_var: str, required: bool = True
    ) -> None:
        """Register that an adapter needs a credential from an env var."""
        self._store[adapter_id] = {
            "env_var": env_var,
            "required": required,
        }

    def get_credential(self, adapter_id: str) -> str | None:
        """Look up credential from env (via os.environ).

        Returns None if not found.
        Never logs, prints, or exposes the raw value.
        """
        entry = self._store.get(adapter_id)
        if entry is None:
            return None
        return os.environ.get(entry["env_var"])

    def has_credential(self, adapter_id: str) -> bool:
        """Check if credential is available."""
        return self.get_credential(adapter_id) is not None

    @staticmethod
    def mask_credential(credential: str) -> str:
        """Mask credential string.

        If length <= 8: return '***'
        Otherwise: show first 4 + '***' + last 4
        """
        if len(credential) <= 8:
            return "***"
        return credential[:4] + "***" + credential[-4:]

    def validate_all(self) -> CredentialValidationResult:
        """Validate all registered adapters have their credentials."""
        missing: list[str] = []
        available: list[str] = []
        for adapter_id in self._store:
            if self.has_credential(adapter_id):
                available.append(adapter_id)
            else:
                missing.append(adapter_id)
        return CredentialValidationResult(
            valid=len(missing) == 0,
            missing=missing,
            available=available,
        )

    def list_registered(self) -> dict[str, dict]:
        """Return registered adapters with their metadata."""
        return {
            adapter_id: {
                "env_var": info["env_var"],
                "required": info["required"],
                "available": self.has_credential(adapter_id),
            }
            for adapter_id, info in self._store.items()
        }

    def summary(self) -> dict:
        """Return stats: total registered, available, missing."""
        registered = self._store.keys()
        total = len(registered)
        available = sum(1 for a in registered if self.has_credential(a))
        return {
            "total": total,
            "available": available,
            "missing": total - available,
        }
