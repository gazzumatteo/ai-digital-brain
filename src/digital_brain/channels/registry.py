"""Channel registry — manages active channel plugins."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from digital_brain.channels.base import ChannelPlugin

logger = logging.getLogger(__name__)


class ChannelRegistry:
    """Registry of active channel plugins.

    Provides lifecycle management (start/stop all channels) and lookup by
    channel ID.
    """

    def __init__(self) -> None:
        self._channels: dict[str, ChannelPlugin] = {}

    def register(self, plugin: ChannelPlugin) -> None:
        """Register a channel plugin.

        Raises ValueError if a plugin with the same channel_id is already
        registered.
        """
        cid = plugin.channel_id()
        if cid in self._channels:
            raise ValueError(f"Channel '{cid}' is already registered")
        self._channels[cid] = plugin
        logger.info("Channel registered: %s", cid)

    def unregister(self, channel_id: str) -> None:
        """Remove a channel plugin from the registry."""
        if channel_id in self._channels:
            del self._channels[channel_id]
            logger.info("Channel unregistered: %s", channel_id)

    def get(self, channel_id: str) -> ChannelPlugin:
        """Retrieve a channel plugin by its ID.

        Raises KeyError if the channel is not registered.
        """
        try:
            return self._channels[channel_id]
        except KeyError:
            raise KeyError(f"Channel '{channel_id}' is not registered") from None

    def list_channels(self) -> list[str]:
        """Return the IDs of all registered channels."""
        return list(self._channels.keys())

    async def start_all(self, abort_signal: asyncio.Event) -> None:
        """Start all registered channels concurrently."""
        if not self._channels:
            logger.warning("No channels registered — nothing to start")
            return

        tasks = []
        for cid, plugin in self._channels.items():
            logger.info("Starting channel: %s", cid)
            tasks.append(plugin.start(abort_signal))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop_all(self) -> None:
        """Stop all registered channels."""
        for cid, plugin in self._channels.items():
            logger.info("Stopping channel: %s", cid)
            try:
                await plugin.stop()
            except Exception:
                logger.exception("Error stopping channel %s", cid)

    async def health_check_all(self) -> dict[str, Any]:
        """Run health checks on all registered channels."""
        results: dict[str, Any] = {}
        for cid, plugin in self._channels.items():
            try:
                results[cid] = await plugin.health_check()
            except Exception as exc:
                results[cid] = {"ok": False, "error": str(exc)}
        return results
