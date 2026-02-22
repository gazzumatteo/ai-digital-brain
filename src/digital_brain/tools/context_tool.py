"""Context signal gathering for the Predictive Engine."""

from __future__ import annotations

from datetime import datetime, timezone

from digital_brain.memory.tools import _get_manager


def get_context_signals(user_id: str) -> dict:
    """Gather contextual signals to support predictive pre-loading.

    Collects environmental and behavioural signals that help the Predictive
    Agent anticipate what the user will need next.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        A dict containing context signals: time_of_day, day_of_week,
        recent_topics, and session metadata.
    """
    now = datetime.now(timezone.utc)
    hour = now.hour

    if hour < 12:
        time_of_day = "morning"
    elif hour < 17:
        time_of_day = "afternoon"
    else:
        time_of_day = "evening"

    day_of_week = now.strftime("%A").lower()
    is_weekend = day_of_week in ("saturday", "sunday")

    # Retrieve recent memories to identify recent topics
    recent_topics: list[str] = []
    try:
        recent = _get_manager().get_recent(user_id=user_id, hours=48)
        recent_topics = [m.memory for m in recent.results[:10]]
    except Exception:
        pass

    return {
        "time_of_day": time_of_day,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "current_hour_utc": hour,
        "recent_topics": recent_topics,
        "recent_topic_count": len(recent_topics),
    }
