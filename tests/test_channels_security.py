"""Tests for channels/security.py — DmPolicyEnforcer."""

from __future__ import annotations

from digital_brain.channels.security import DmPolicy, DmPolicyEnforcer


class TestDmPolicyEnforcer:
    def test_open_allows_everyone(self):
        enforcer = DmPolicyEnforcer(policy="open")
        allowed, reason = enforcer.check_access("telegram", "12345")
        assert allowed is True
        assert reason == "ok"

    def test_disabled_blocks_everyone(self):
        enforcer = DmPolicyEnforcer(policy="disabled")
        allowed, reason = enforcer.check_access("telegram", "12345")
        assert allowed is False
        assert reason == "dm_disabled"

    def test_pairing_blocks_unknown(self):
        enforcer = DmPolicyEnforcer(policy="pairing")
        allowed, reason = enforcer.check_access("telegram", "unknown_user")
        assert allowed is False
        assert reason == "awaiting_pairing"

    def test_pairing_allows_listed_user(self):
        enforcer = DmPolicyEnforcer(
            policy="pairing",
            allow_from=["telegram:12345"],
        )
        allowed, reason = enforcer.check_access("telegram", "12345")
        assert allowed is True
        assert reason == "ok"

    def test_pairing_pending_set(self):
        enforcer = DmPolicyEnforcer(policy="pairing")
        enforcer.check_access("telegram", "new_user")
        assert "telegram:new_user" in enforcer.pending

    def test_approve_moves_to_allowlist(self):
        enforcer = DmPolicyEnforcer(policy="pairing")
        enforcer.check_access("telegram", "user1")
        assert "telegram:user1" in enforcer.pending

        enforcer.approve("telegram", "user1")
        assert "telegram:user1" not in enforcer.pending
        assert "telegram:user1" in enforcer.allowed

        allowed, reason = enforcer.check_access("telegram", "user1")
        assert allowed is True

    def test_deny_removes_from_pending(self):
        enforcer = DmPolicyEnforcer(policy="pairing")
        enforcer.check_access("telegram", "user1")
        enforcer.deny("telegram", "user1")
        assert "telegram:user1" not in enforcer.pending

    def test_revoke_removes_from_allowlist(self):
        enforcer = DmPolicyEnforcer(policy="pairing", allow_from=["telegram:user1"])
        enforcer.revoke("telegram", "user1")
        assert "telegram:user1" not in enforcer.allowed

        allowed, _ = enforcer.check_access("telegram", "user1")
        assert allowed is False

    def test_allow_from_as_list(self):
        enforcer = DmPolicyEnforcer(policy="pairing", allow_from=["telegram:a", "telegram:b"])
        assert enforcer.check_access("telegram", "a")[0] is True
        assert enforcer.check_access("telegram", "b")[0] is True
        assert enforcer.check_access("telegram", "c")[0] is False

    def test_channel_scoping(self):
        """A user approved on telegram should not be auto-approved on discord."""
        enforcer = DmPolicyEnforcer(policy="pairing", allow_from=["telegram:123"])
        assert enforcer.check_access("telegram", "123")[0] is True
        assert enforcer.check_access("discord", "123")[0] is False

    def test_policy_property(self):
        enforcer = DmPolicyEnforcer(policy="open")
        assert enforcer.policy == DmPolicy.OPEN

    def test_policy_enum_input(self):
        enforcer = DmPolicyEnforcer(policy=DmPolicy.DISABLED)
        assert enforcer.policy == DmPolicy.DISABLED
