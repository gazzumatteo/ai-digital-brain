#!/usr/bin/env python3
"""Manually trigger the Reflection Agent for a user."""

from __future__ import annotations

import asyncio
import sys

from digital_brain.agents.orchestrator import DigitalBrainOrchestrator


async def main(user_id: str) -> None:
    orchestrator = DigitalBrainOrchestrator()
    print(f"Running reflection for user '{user_id}'…")
    summary = await orchestrator.reflect(user_id=user_id)
    print(f"\n--- Reflection Summary ---\n{summary}")


if __name__ == "__main__":
    uid = sys.argv[1] if len(sys.argv) > 1 else "demo_user"
    asyncio.run(main(uid))
