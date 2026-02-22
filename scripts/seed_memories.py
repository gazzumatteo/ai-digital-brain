#!/usr/bin/env python3
"""Seed the memory store with sample data for demonstration."""

from __future__ import annotations

import sys

from digital_brain.memory.manager import MemoryManager

SAMPLE_MEMORIES = [
    "User's name is Alice",
    "User works as a software engineer at Acme Corp",
    "User prefers morning meetings before 10am",
    "User is vegetarian",
    "User's dog is named Max",
    "User is currently working on Project Alpha — a customer portal redesign",
    "User's manager is Sarah",
    "User prefers Python over JavaScript",
    "User has a meeting with the design team every Tuesday at 2pm",
    "User is interested in machine learning and cognitive architectures",
]


def main(user_id: str = "demo_user") -> None:
    manager = MemoryManager()
    print(f"Seeding {len(SAMPLE_MEMORIES)} memories for user '{user_id}'…")
    for i, fact in enumerate(SAMPLE_MEMORIES, 1):
        result = manager.add(fact, user_id=user_id, infer=False)
        print(f"  [{i}/{len(SAMPLE_MEMORIES)}] {fact}")
    print("Done.")


if __name__ == "__main__":
    uid = sys.argv[1] if len(sys.argv) > 1 else "demo_user"
    main(uid)
