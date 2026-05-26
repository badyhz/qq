"""Tests for core/credential_manager.py."""

from __future__ import annotations

import pytest

from core.credential_manager import (
    CredentialManager,
    CredentialValidationResult,
    MissingCredentialError,
)


class TestRegisterAdapter:
    def test_register_single(self) -> None:
        cm = CredentialManager()
        cm.register_adapter("binance", "BINANCE_API_KEY")
        assert "binance" in cm.list_registered()

    def test_register_multiple_independent(self) -> None:
        cm = CredentialManager()
        cm.register_adapter("binance", "BINANCE_API_KEY")
        cm.register_adapter("okx", "OKX_API_KEY")
        info = cm.list_registered()
        assert "binance" in info
        assert "okx" in info
        assert info["binance"]["env_var"] == "BINANCE_API_KEY"
        assert info["okx"]["env_var"] == "OKX_API_KEY"

    def test_register_optional(self) -> None:
        cm = CredentialManager()
        cm.register_adapter("slack", "SLACK_TOKEN", required=False)
        info = cm.list_registered()
        assert info["slack"]["required"] is False

    def test_register_required_default(self) -> None:
        cm = CredentialManager()
        cm.register_adapter("binance", "BINANCE_API_KEY")
        info = cm.list_registered()
        assert info["binance"]["required"] is True


class TestGetCredential:
    def test_get_credential_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cm = CredentialManager()
        cm.register_adapter("binance", "BINANCE_API_KEY")
        monkeypatch.setenv("BINANCE_API_KEY", "abc123secret")
        assert cm.get_credential("binance") == "abc123secret"

    def test_get_credential_not_found(self) -> None:
        cm = CredentialManager()
        cm.register_adapter("binance", "BINANCE_API_KEY")
        assert cm.get_credential("binance") is None

    def test_get_credential_unregistered(self) -> None:
        cm = CredentialManager()
        assert cm.get_credential("nonexistent") is None

    def test_env_cleaned_up_after_test(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cm = CredentialManager()
        cm.register_adapter("binance", "BINANCE_TEST_CLEANUP")
        monkeypatch.setenv("BINANCE_TEST_CLEANUP", "temp")
        assert cm.get_credential("binance") == "temp"
        # monkeypatch auto-restores; verify is None after scope exits
        # (tested implicitly by isolation between tests)


class TestHasCredential:
    def test_has_credential_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cm = CredentialManager()
        cm.register_adapter("binance", "BINANCE_API_KEY")
        monkeypatch.setenv("BINANCE_API_KEY", "key123")
        assert cm.has_credential("binance") is True

    def test_has_credential_false(self) -> None:
        cm = CredentialManager()
        cm.register_adapter("binance", "BINANCE_API_KEY")
        assert cm.has_credential("binance") is False

    def test_has_credential_unregistered(self) -> None:
        cm = CredentialManager()
        assert cm.has_credential("nonexistent") is False


class TestMaskCredential:
    def test_short_key_returns_stars(self) -> None:
        assert CredentialManager.mask_credential("abc") == "***"
        assert CredentialManager.mask_credential("12345678") == "***"

    def test_exactly_8_returns_stars(self) -> None:
        assert CredentialManager.mask_credential("abcdefgh") == "***"

    def test_long_key_shows_first_last_4(self) -> None:
        result = CredentialManager.mask_credential("abcdefghijklmnop")
        assert result == "abcd***mnop"

    def test_9_char_key(self) -> None:
        result = CredentialManager.mask_credential("123456789")
        assert result == "1234***6789"

    def test_empty_string(self) -> None:
        assert CredentialManager.mask_credential("") == "***"


class TestValidateAll:
    def test_all_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cm = CredentialManager()
        cm.register_adapter("binance", "BINANCE_KEY")
        cm.register_adapter("okx", "OKX_KEY")
        monkeypatch.setenv("BINANCE_KEY", "bkey")
        monkeypatch.setenv("OKX_KEY", "okey")
        result = cm.validate_all()
        assert result.valid is True
        assert result.missing == []
        assert set(result.available) == {"binance", "okx"}

    def test_some_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cm = CredentialManager()
        cm.register_adapter("binance", "BINANCE_KEY")
        cm.register_adapter("okx", "OKX_KEY")
        monkeypatch.setenv("BINANCE_KEY", "bkey")
        # OKX_KEY not set
        result = cm.validate_all()
        assert result.valid is False
        assert "okx" in result.missing
        assert "binance" in result.available

    def test_all_missing(self) -> None:
        cm = CredentialManager()
        cm.register_adapter("binance", "BINANCE_KEY")
        cm.register_adapter("okx", "OKX_KEY")
        result = cm.validate_all()
        assert result.valid is False
        assert set(result.missing) == {"binance", "okx"}
        assert result.available == []

    def test_empty_store(self) -> None:
        cm = CredentialManager()
        result = cm.validate_all()
        assert result.valid is True
        assert result.missing == []
        assert result.available == []


class TestListRegistered:
    def test_list_after_register(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cm = CredentialManager()
        cm.register_adapter("binance", "BINANCE_KEY")
        monkeypatch.setenv("BINANCE_KEY", "x")
        info = cm.list_registered()
        assert info == {
            "binance": {"env_var": "BINANCE_KEY", "required": True, "available": True}
        }

    def test_list_missing_not_available(self) -> None:
        cm = CredentialManager()
        cm.register_adapter("binance", "BINANCE_KEY")
        info = cm.list_registered()
        assert info["binance"]["available"] is False

    def test_list_optional_adapter(self) -> None:
        cm = CredentialManager()
        cm.register_adapter("slack", "SLACK_TOKEN", required=False)
        info = cm.list_registered()
        assert info["slack"]["required"] is False
        assert info["slack"]["available"] is False


class TestSummary:
    def test_summary_all_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cm = CredentialManager()
        cm.register_adapter("a", "A_KEY")
        cm.register_adapter("b", "B_KEY")
        monkeypatch.setenv("A_KEY", "a")
        monkeypatch.setenv("B_KEY", "b")
        s = cm.summary()
        assert s == {"total": 2, "available": 2, "missing": 0}

    def test_summary_some_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cm = CredentialManager()
        cm.register_adapter("a", "A_KEY")
        cm.register_adapter("b", "B_KEY")
        monkeypatch.setenv("A_KEY", "a")
        s = cm.summary()
        assert s == {"total": 2, "available": 1, "missing": 1}

    def test_summary_empty(self) -> None:
        cm = CredentialManager()
        s = cm.summary()
        assert s == {"total": 0, "available": 0, "missing": 0}


class TestMissingCredentialError:
    def test_fields(self) -> None:
        err = MissingCredentialError("binance", "BINANCE_KEY")
        assert err.adapter_id == "binance"
        assert err.env_var == "BINANCE_KEY"
        assert "binance" in str(err)
        assert "BINANCE_KEY" in str(err)

    def test_is_exception(self) -> None:
        err = MissingCredentialError("a", "A_KEY")
        assert isinstance(err, Exception)


class TestCredentialValidationResult:
    def test_dataclass_fields(self) -> None:
        r = CredentialValidationResult(valid=True, missing=[], available=["a"])
        assert r.valid is True
        assert r.missing == []
        assert r.available == ["a"]

    def test_defaults(self) -> None:
        r = CredentialValidationResult(valid=False)
        assert r.missing == []
        assert r.available == []
