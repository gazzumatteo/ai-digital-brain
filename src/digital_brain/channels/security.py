"""DM policy enforcement — controls who can interact with the Digital Brain."""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class DmPolicy(str, Enum):
    """Access control policy for direct messages."""

    OPEN = "open"
    """Anyone can message the bot."""

    PAIRING = "pairing"
    """Only approved senders can message; unknown senders enter a pending state."""

    DISABLED = "disabled"
    """DMs are completely blocked."""


class AccessDeniedError(Exception):
    """Raised when a sender is not allowed to interact."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class DmPolicyEnforcer:
    """Enforces access control based on the configured DM policy.

    Supports three modes:

    - **open**: everyone is allowed.
    - **pairing**: only senders in the allowlist are permitted.  Unknown
      senders are added to a pending set for manual approval.
    - **disabled**: all messages are rejected.

    Parameters
    ----------
    policy:
        One of "open", "pairing", "disabled".
    allow_from:
        Set of sender identifiers that are pre-approved.  The identifiers
        are channel-scoped strings, e.g. ``"telegram:123456"``.
    """

    def __init__(
        self,
        policy: str | DmPolicy = DmPolicy.PAIRING,
        allow_from: set[str] | list[str] | None = None,
    ) -> None:
        self._policy = DmPolicy(policy)
        self._allow_from: set[str] = set(allow_from) if allow_from else set()
        self._pending: set[str] = set()

    @property
    def policy(self) -> DmPolicy:
        return self._policy

    def _scoped_id(self, channel: str, sender_id: str) -> str:
        return f"{channel}:{sender_id}"

    def check_access(self, channel: str, sender_id: str) -> tuple[bool, str]:
        """Check whether *sender_id* on *channel* is allowed to interact.

        Returns a ``(allowed, reason)`` tuple.
        """
        if self._policy == DmPolicy.DISABLED:
            return False, "dm_disabled"

        if self._policy == DmPolicy.OPEN:
            return True, "ok"

        # Pairing mode
        scoped = self._scoped_id(channel, sender_id)
        if scoped in self._allow_from:
            return True, "ok"

        self._pending.add(scoped)
        logger.info("Sender pending approval: %s", scoped)
        return False, "awaiting_pairing"

    def approve(self, channel: str, sender_id: str) -> None:
        """Approve a pending sender, moving them to the allowlist."""
        scoped = self._scoped_id(channel, sender_id)
        self._pending.discard(scoped)
        self._allow_from.add(scoped)
        logger.info("Sender approved: %s", scoped)

    def deny(self, channel: str, sender_id: str) -> None:
        """Deny a pending sender, removing them from the pending set."""
        scoped = self._scoped_id(channel, sender_id)
        self._pending.discard(scoped)
        logger.info("Sender denied: %s", scoped)

    def revoke(self, channel: str, sender_id: str) -> None:
        """Revoke access for a previously approved sender."""
        scoped = self._scoped_id(channel, sender_id)
        self._allow_from.discard(scoped)
        logger.info("Sender access revoked: %s", scoped)

    @property
    def pending(self) -> frozenset[str]:
        """Return the set of senders awaiting approval."""
        return frozenset(self._pending)

    @property
    def allowed(self) -> frozenset[str]:
        """Return the current allowlist."""
        return frozenset(self._allow_from)
