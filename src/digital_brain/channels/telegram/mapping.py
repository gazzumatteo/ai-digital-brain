"""User ID mapping — maps Telegram user IDs to Digital Brain user IDs."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class TelegramUserMapper:
    """Maps Telegram user IDs to Digital Brain internal user IDs.

    On first interaction a mapping is automatically created.  The mapping is
    stored in memory (dict) for now; a persistent backend can be plugged in
    later.
    """

    def __init__(self) -> None:
        # telegram_user_id -> brain_user_id
        self._map: dict[str, str] = {}
        # brain_user_id -> telegram display name (for reference)
        self._names: dict[str, str] = {}

    def resolve(self, telegram_user_id: int | str, display_name: str = "") -> str:
        """Resolve a Telegram user ID to a brain user ID.

        Creates the mapping automatically on first encounter.
        """
        tg_id = str(telegram_user_id)

        if tg_id in self._map:
            return self._map[tg_id]

        # Auto-create: use "tg_<id>" as the brain user ID
        brain_id = f"tg_{tg_id}"
        self._map[tg_id] = brain_id
        if display_name:
            self._names[brain_id] = display_name

        logger.info(
            "New Telegram user mapped: tg=%s -> brain=%s name=%s",
            tg_id,
            brain_id,
            display_name,
        )
        return brain_id

    def get_brain_id(self, telegram_user_id: int | str) -> str | None:
        """Look up the brain user ID for a Telegram user, or None."""
        return self._map.get(str(telegram_user_id))

    def get_display_name(self, brain_user_id: str) -> str | None:
        """Look up the display name for a brain user ID."""
        return self._names.get(brain_user_id)

    def set_display_name(self, brain_user_id: str, name: str) -> None:
        """Update the display name for a brain user."""
        self._names[brain_user_id] = name
