"""
Tests for the DropDirectoryScanner module.

Validates file discovery, chunking strategies, classification,
minimum-length filtering, and JSON output.
"""

import json
from pathlib import Path


# Add ai-assistant/src to path so the scanner can be imported
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ai-assistant" / "src"))

from drop_directory_scanner import DropDirectoryScanner, _classify_document_type


# ---------------------------------------------------------------------------
# Test 1: Discover supported files
# ---------------------------------------------------------------------------


def test_discover_supported_files(tmp_path):
    """Scanner finds .md, .yml, .txt and ignores .py files."""
    src = tmp_path / "docs"
    src.mkdir()
    (src / "readme.md").write_text("# Hello")
    (src / "config.yml").write_text("key: value")
    (src / "notes.txt").write_text("Some notes")
    (src / "script.py").write_text("print('hi')")

    scanner = DropDirectoryScanner(source_dirs=[src], output_dir=tmp_path / "out")
    files = scanner.discover_files()
    extensions = {f[0].suffix for f in files}

    assert ".md" in extensions
    assert ".yml" in extensions
    assert ".txt" in extensions
    assert ".py" not in extensions


# ---------------------------------------------------------------------------
# Test 2: Discover recurses subdirectories
# ---------------------------------------------------------------------------


def test_discover_recurses_subdirs(tmp_path):
    """Scanner finds files in nested subdirectories."""
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    (nested / "deep.md").write_text("# Deep file\n\nSome content here that is long enough to be a chunk.")

    scanner = DropDirectoryScanner(source_dirs=[tmp_path], output_dir=tmp_path / "out")
    files = scanner.discover_files()

    assert len(files) == 1
    assert files[0][0].name == "deep.md"


# ---------------------------------------------------------------------------
# Test 3: Chunk markdown by headers
# ---------------------------------------------------------------------------


def test_chunk_markdown_by_headers(tmp_path):
    """Markdown files are split at # headers."""
    src = tmp_path / "docs"
    src.mkdir()
    content = (
        "# Section One\n\n"
        "This is the first section with enough content to pass the minimum length filter easily.\n\n"
        "## Section Two\n\n"
        "This is the second section with enough content to pass the minimum length filter easily.\n"
    )
    (src / "guide.md").write_text(content)

    scanner = DropDirectoryScanner(source_dirs=[src], output_dir=tmp_path / "out")
    files_processed, chunks_generated = scanner.scan_and_process()

    assert files_processed == 1
    assert chunks_generated == 2

    chunks = json.loads((tmp_path / "out" / "document_chunks.json").read_text())
    titles = [c["title"] for c in chunks]
    assert "Section One" in titles
    assert "Section Two" in titles


# ---------------------------------------------------------------------------
# Test 4: Chunk YAML as whole file
# ---------------------------------------------------------------------------


def test_chunk_yaml_whole_file(tmp_path):
    """YAML files produce a single chunk containing the entire file content."""
    src = tmp_path / "configs"
    src.mkdir()
    yaml_content = "key: value\nlist:\n  - item1\n  - item2\n  - item3\nextra: data that makes this long enough"
    (src / "config.yml").write_text(yaml_content)

    scanner = DropDirectoryScanner(source_dirs=[src], output_dir=tmp_path / "out")
    files_processed, chunks_generated = scanner.scan_and_process()

    assert files_processed == 1
    assert chunks_generated == 1

    chunks = json.loads((tmp_path / "out" / "document_chunks.json").read_text())
    assert chunks[0]["content"] == yaml_content.strip()


# ---------------------------------------------------------------------------
# Test 5: Chunk text by paragraphs
# ---------------------------------------------------------------------------


def test_chunk_text_by_paragraphs(tmp_path):
    """Text files are split at double newlines (paragraph boundaries)."""
    src = tmp_path / "notes"
    src.mkdir()
    content = (
        "First paragraph with enough content to pass the minimum character length.\n\n"
        "Second paragraph also with enough content to pass the minimum character length.\n\n"
        "Third paragraph with even more text content for the minimum length test here."
    )
    (src / "notes.txt").write_text(content)

    scanner = DropDirectoryScanner(source_dirs=[src], output_dir=tmp_path / "out")
    files_processed, chunks_generated = scanner.scan_and_process()

    assert files_processed == 1
    assert chunks_generated == 3


# ---------------------------------------------------------------------------
# Test 6: Classify ADR by filename
# ---------------------------------------------------------------------------


def test_classify_adr_by_filename():
    """Files matching adr-*.md are classified as document_type 'adr'."""
    assert _classify_document_type(Path("adr-0001.md")) == "adr"
    assert _classify_document_type(Path("adr-0045-dag-standards.md")) == "adr"
    assert _classify_document_type(Path("docs/adrs/adr-0063.md")) == "adr"


# ---------------------------------------------------------------------------
# Test 7: Classify markdown default
# ---------------------------------------------------------------------------


def test_classify_markdown_default():
    """Non-ADR .md files are classified as 'markdown'."""
    assert _classify_document_type(Path("readme.md")) == "markdown"
    assert _classify_document_type(Path("guide.md")) == "markdown"
    assert _classify_document_type(Path("docs/overview.md")) == "markdown"


# ---------------------------------------------------------------------------
# Test 8: Short content skipped
# ---------------------------------------------------------------------------


def test_short_content_skipped(tmp_path):
    """Chunks under 50 characters are excluded from output."""
    src = tmp_path / "docs"
    src.mkdir()
    # Two sections: one too short, one long enough
    content = "# Short\n\nTiny.\n\n" "# Long Section\n\n" "This section has enough content to pass the fifty character minimum length requirement easily."
    (src / "mixed.md").write_text(content)

    scanner = DropDirectoryScanner(source_dirs=[src], output_dir=tmp_path / "out")
    _, chunks_generated = scanner.scan_and_process()

    assert chunks_generated == 1
    chunks = json.loads((tmp_path / "out" / "document_chunks.json").read_text())
    assert "Long Section" in chunks[0]["title"]


# ---------------------------------------------------------------------------
# Test 9: Write chunks produces valid JSON with expected schema
# ---------------------------------------------------------------------------


def test_write_chunks_valid_json(tmp_path):
    """Output file is valid JSON and each chunk has required fields."""
    src = tmp_path / "docs"
    src.mkdir()
    (src / "adr-0001.md").write_text("# ADR 0001\n\nThis is a test ADR with enough content to be included as a chunk.")

    scanner = DropDirectoryScanner(source_dirs=[src], output_dir=tmp_path / "out")
    scanner.scan_and_process()

    chunks_file = tmp_path / "out" / "document_chunks.json"
    assert chunks_file.exists()

    chunks = json.loads(chunks_file.read_text())
    assert isinstance(chunks, list)
    assert len(chunks) > 0

    required_keys = {"id", "source_file", "title", "content", "chunk_type", "metadata", "word_count", "created_at"}
    for chunk in chunks:
        assert required_keys.issubset(chunk.keys()), f"Missing keys: {required_keys - chunk.keys()}"
        assert isinstance(chunk["metadata"], dict)
        assert "document_type" in chunk["metadata"]
        assert chunk["metadata"]["document_type"] == "adr"


# ---------------------------------------------------------------------------
# Test 10: Empty dirs produce zero chunks without crash
# ---------------------------------------------------------------------------


def test_empty_dirs_produce_zero_chunks(tmp_path):
    """Scanning empty or nonexistent dirs returns 0 files, 0 chunks, no crash."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    nonexistent = tmp_path / "no_such_dir"

    scanner = DropDirectoryScanner(
        source_dirs=[empty_dir, nonexistent],
        output_dir=tmp_path / "out",
    )
    files_processed, chunks_generated = scanner.scan_and_process()

    assert files_processed == 0
    assert chunks_generated == 0

    # Output file should still be created (with empty list)
    chunks_file = tmp_path / "out" / "document_chunks.json"
    assert chunks_file.exists()
    assert json.loads(chunks_file.read_text()) == []
