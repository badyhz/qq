"""Tests for read-only hook permissions — pure pytest, no I/O."""
from core.read_only_hook_permissions import (
    VALID_PERMISSIONS,
    ReadOnlyPermission,
    check_permission,
    classify_denied_operation,
    permission_to_dict,
)


class TestPermissions:
    def test_read_granted(self):
        perm = check_permission("read")
        assert isinstance(perm, ReadOnlyPermission)
        assert perm.granted is True
        assert perm.denial_reason == ""

    def test_write_denied(self):
        perm = check_permission("write")
        assert perm.granted is False
        assert "denied" in perm.denial_reason.lower()

    def test_classify_trade(self):
        assert classify_denied_operation("trade") == "TRADE"
        assert classify_denied_operation("write") == "WRITE"
        assert classify_denied_operation("execute") == "EXECUTE"
        assert classify_denied_operation("unknown_op") == "UNKNOWN"

    def test_valid_permissions(self):
        assert "read" in VALID_PERMISSIONS
        assert "query" in VALID_PERMISSIONS
        assert "inspect" in VALID_PERMISSIONS
        assert "validate" in VALID_PERMISSIONS
        assert "report" in VALID_PERMISSIONS
