"""Multi-channel messaging layer for the Digital Brain."""

from digital_brain.channels.base import (
    ChannelPlugin,
    InboundMessage,
    MediaAttachment,
    OutboundResult,
)
from digital_brain.channels.registry import ChannelRegistry

__all__ = [
    "ChannelPlugin",
    "ChannelRegistry",
    "InboundMessage",
    "MediaAttachment",
    "OutboundResult",
]
