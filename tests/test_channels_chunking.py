"""Tests for channels/chunking.py — text and markdown chunking."""

from __future__ import annotations

from digital_brain.channels.chunking import ChunkMode, chunk_text


class TestChunkText:
    def test_empty_string(self):
        assert chunk_text("") == []

    def test_short_text_returns_single_chunk(self):
        assert chunk_text("hello world", limit=100) == ["hello world"]

    def test_exact_limit(self):
        text = "x" * 100
        assert chunk_text(text, limit=100) == [text]


class TestPlainChunking:
    def test_splits_on_paragraph(self):
        text = "First paragraph.\n\nSecond paragraph."
        chunks = chunk_text(text, limit=25, mode=ChunkMode.TEXT)
        assert len(chunks) == 2
        assert "First" in chunks[0]
        assert "Second" in chunks[1]

    def test_splits_on_newline(self):
        text = "Line one.\nLine two.\nLine three."
        chunks = chunk_text(text, limit=20, mode=ChunkMode.TEXT)
        assert len(chunks) >= 2

    def test_splits_on_space(self):
        text = "word " * 20
        chunks = chunk_text(text.strip(), limit=30, mode=ChunkMode.TEXT)
        assert all(len(c) <= 30 for c in chunks)

    def test_hard_split_no_separator(self):
        text = "a" * 200
        chunks = chunk_text(text, limit=50, mode=ChunkMode.TEXT)
        assert all(len(c) <= 50 for c in chunks)
        assert "".join(chunks) == text

    def test_real_world_text(self):
        text = (
            "Il Digital Brain è un progetto che implementa un'architettura cognitiva "
            "per agenti AI con memoria persistente.\n\n"
            "Si basa su tre agenti principali: Conversation, Reflection e Predictive.\n\n"
            "Il Conversation Agent gestisce il dialogo con l'utente, "
            "cercando nella memoria informazioni rilevanti prima di rispondere."
        )
        chunks = chunk_text(text, limit=150, mode=ChunkMode.TEXT)
        assert len(chunks) >= 2
        assert all(len(c) <= 150 for c in chunks)


class TestMarkdownChunking:
    def test_preserves_code_block(self):
        text = "Some text.\n\n```python\nprint('hello')\nprint('world')\n```\n\nMore text."
        chunks = chunk_text(text, limit=5000, mode=ChunkMode.MARKDOWN)
        # Should fit in one chunk
        assert len(chunks) == 1
        assert "```python" in chunks[0]

    def test_splits_around_code_block(self):
        intro = "A" * 100
        code = "```python\n" + ("x = 1\n" * 5) + "```"
        outro = "B" * 100
        text = f"{intro}\n\n{code}\n\n{outro}"

        chunks = chunk_text(text, limit=130, mode=ChunkMode.MARKDOWN)
        assert len(chunks) >= 2

    def test_oversized_code_block_rewrapped(self):
        code_body = "\n".join(f"line_{i} = {i}" for i in range(50))
        text = f"```python\n{code_body}\n```"
        chunks = chunk_text(text, limit=200, mode=ChunkMode.MARKDOWN)
        # Each chunk should be wrapped in fences
        for chunk in chunks:
            assert chunk.startswith("```python")
            assert chunk.endswith("```")

    def test_heading_not_split(self):
        text = "# My Heading\n\nSome paragraph text here."
        chunks = chunk_text(text, limit=5000, mode=ChunkMode.MARKDOWN)
        assert len(chunks) == 1
        assert "# My Heading" in chunks[0]

    def test_list_preserved(self):
        text = "Items:\n\n- Item one\n- Item two\n- Item three"
        chunks = chunk_text(text, limit=5000, mode=ChunkMode.MARKDOWN)
        assert len(chunks) == 1
        assert "- Item one" in chunks[0]

    def test_mixed_content(self):
        text = (
            "# Title\n\n"
            "Some intro text.\n\n"
            "```bash\necho hello\n```\n\n"
            "- Point A\n"
            "- Point B\n\n"
            "Conclusion."
        )
        chunks = chunk_text(text, limit=5000, mode=ChunkMode.MARKDOWN)
        assert len(chunks) == 1

    def test_default_mode_is_text(self):
        text = "a " * 100
        # Default mode should be TEXT
        chunks = chunk_text(text.strip(), limit=50)
        assert all(len(c) <= 50 for c in chunks)
