"""Outbound text chunking — splits long responses for channel delivery."""

from __future__ import annotations

import re
from enum import Enum


class ChunkMode(str, Enum):
    """Chunking strategy."""

    TEXT = "text"
    """Greedy split by character limit (for channels without markdown)."""

    MARKDOWN = "markdown"
    """Markdown-aware split that preserves code blocks, lists, headings."""


def chunk_text(text: str, limit: int = 4096, mode: ChunkMode = ChunkMode.TEXT) -> list[str]:
    """Split *text* into chunks that fit within *limit* characters.

    Parameters
    ----------
    text:
        The full text to split.
    limit:
        Maximum characters per chunk.
    mode:
        ``"text"`` for greedy splitting, ``"markdown"`` for structure-aware
        splitting that avoids breaking code blocks and lists.
    """
    if not text:
        return []

    if len(text) <= limit:
        return [text]

    if mode == ChunkMode.MARKDOWN:
        return _chunk_markdown(text, limit)
    return _chunk_plain(text, limit)


def _chunk_plain(text: str, limit: int) -> list[str]:
    """Greedy split on paragraph / line / word boundaries."""
    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break

        # Try to break at a double newline (paragraph boundary)
        cut = _find_break(remaining, limit, "\n\n")
        if cut == -1:
            # Fall back to single newline
            cut = _find_break(remaining, limit, "\n")
        if cut == -1:
            # Fall back to space
            cut = _find_break(remaining, limit, " ")
        if cut == -1:
            # Hard cut at limit
            cut = limit

        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()

    return chunks


def _find_break(text: str, limit: int, sep: str) -> int:
    """Find the last occurrence of *sep* within *limit* characters."""
    idx = text.rfind(sep, 0, limit)
    if idx > 0:
        return idx + len(sep)
    return -1


# Regex matching the opening of a fenced code block
_CODE_FENCE_RE = re.compile(r"^(`{3,}|~{3,})", re.MULTILINE)


def _chunk_markdown(text: str, limit: int) -> list[str]:
    """Markdown-aware chunking.

    Ensures that fenced code blocks, lists and headings are not split in the
    middle.  If a code block exceeds the limit by itself, it is hard-split but
    re-wrapped with fences so each chunk is valid markdown.
    """
    blocks = _split_into_blocks(text)
    chunks: list[str] = []
    current = ""

    for block in blocks:
        candidate = (current + "\n\n" + block).strip() if current else block

        if len(candidate) <= limit:
            current = candidate
            continue

        # The current accumulator is full — flush it
        if current:
            chunks.append(current)

        # If this single block fits, start a new accumulator
        if len(block) <= limit:
            current = block
            continue

        # Block itself exceeds the limit — need to split it
        for sub in _split_oversized_block(block, limit):
            if len(sub) <= limit:
                chunks.append(sub)
            else:
                # Absolute fallback: hard-cut
                chunks.extend(_chunk_plain(sub, limit))
        current = ""

    if current:
        chunks.append(current)

    return chunks


def _split_into_blocks(text: str) -> list[str]:
    """Split markdown text into logical blocks.

    A block is either a fenced code block or a sequence of lines separated
    by blank lines.
    """
    blocks: list[str] = []
    lines = text.split("\n")
    current_lines: list[str] = []
    in_fence = False
    fence_pattern = ""

    for line in lines:
        fence_match = _CODE_FENCE_RE.match(line)

        if fence_match and not in_fence:
            # Starting a code block — flush any accumulated text first
            if current_lines:
                _flush_text_block(current_lines, blocks)
                current_lines = []
            in_fence = True
            fence_pattern = fence_match.group(1)[0]  # ` or ~
            current_lines.append(line)
        elif (
            in_fence
            and line.strip().startswith(fence_pattern)
            and len(line.strip()) >= len(fence_pattern)
        ):
            # Check if this closes the code fence
            stripped = line.strip()
            if stripped == fence_pattern * len(stripped) and stripped[0] == fence_pattern:
                current_lines.append(line)
                blocks.append("\n".join(current_lines))
                current_lines = []
                in_fence = False
            else:
                current_lines.append(line)
        elif in_fence:
            current_lines.append(line)
        elif line.strip() == "":
            # Blank line — potential block boundary
            if current_lines:
                _flush_text_block(current_lines, blocks)
                current_lines = []
        else:
            current_lines.append(line)

    # Remaining lines
    if current_lines:
        if in_fence:
            # Unclosed code block — close it
            current_lines.append(fence_pattern * 3)
        _flush_text_block(current_lines, blocks)

    return blocks


def _flush_text_block(lines: list[str], blocks: list[str]) -> None:
    block = "\n".join(lines).strip()
    if block:
        blocks.append(block)


def _split_oversized_block(block: str, limit: int) -> list[str]:
    """Split a single oversized block.

    For code blocks, re-wraps each chunk with fences.  For text, delegates
    to plain chunking.
    """
    fence_match = _CODE_FENCE_RE.match(block)
    if not fence_match:
        return _chunk_plain(block, limit)

    # It's a code block — extract fence and content
    fence = fence_match.group(1)
    lines = block.split("\n")
    header = lines[0]  # e.g. ```python

    # Check if last line is the closing fence
    if lines[-1].strip().startswith(fence[0]):
        body_lines = lines[1:-1]
    else:
        body_lines = lines[1:]

    body = "\n".join(body_lines)
    # Reserve space for fences
    inner_limit = limit - len(header) - len(fence) - 4  # 2 newlines + margin
    if inner_limit < 100:
        inner_limit = 100

    body_chunks = _chunk_plain(body, inner_limit)
    result = []
    for chunk in body_chunks:
        result.append(f"{header}\n{chunk}\n{fence}")
    return result
