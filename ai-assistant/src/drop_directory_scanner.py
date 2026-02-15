"""
Drop Directory Scanner for RAG document ingestion.

Scans configured source directories for supported document files,
chunks them by type, and writes document_chunks.json for the
Qdrant RAG service to ingest.

Supported file types:
- .md  -> split by # headers (document_type: "adr" if adr-*.md, else "markdown")
- .yml/.yaml -> whole file as one chunk (document_type: "config")
- .rst -> split by double-newline paragraphs (document_type: "documentation")
- .txt -> split by double-newline paragraphs (document_type: "text")
"""

import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".md", ".yml", ".yaml", ".rst", ".txt"}

# Minimum character length for a chunk to be included
MIN_CHUNK_LENGTH = 50


def _classify_document_type(path: Path) -> str:
    """Determine document_type from file path and extension."""
    suffix = path.suffix.lower()
    if suffix == ".md":
        # ADR files match adr-*.md pattern
        if re.match(r"adr-\d+", path.stem, re.IGNORECASE):
            return "adr"
        return "markdown"
    if suffix in (".yml", ".yaml"):
        return "config"
    if suffix == ".rst":
        return "documentation"
    if suffix == ".txt":
        return "text"
    return "unknown"


def _chunk_markdown(content: str) -> List[Tuple[str, str]]:
    """Split markdown by # headers. Returns list of (title, section_content)."""
    lines = content.split("\n")
    sections: List[Tuple[str, str]] = []
    current_title = None
    current_content: List[str] = []

    for line in lines:
        if line.startswith("#"):
            if current_content:
                sections.append((current_title, "\n".join(current_content)))
            current_title = line.lstrip("#").strip()
            current_content = [line]
        else:
            current_content.append(line)

    if current_content:
        sections.append((current_title, "\n".join(current_content)))

    return sections


def _chunk_by_paragraphs(content: str) -> List[Tuple[str, str]]:
    """Split content by double-newline paragraphs. Returns (None, paragraph) tuples."""
    paragraphs = re.split(r"\n\s*\n", content)
    return [(None, p.strip()) for p in paragraphs if p.strip()]


def _chunk_whole_file(content: str, filename: str) -> List[Tuple[str, str]]:
    """Return the whole file as a single chunk."""
    return [(filename, content.strip())]


def _chunk_id(relative_path: str, section_index: int, title: str) -> str:
    """Generate a stable chunk ID from path, index, and title."""
    raw = f"{relative_path}_{section_index}_{title}"
    return hashlib.md5(raw.encode()).hexdigest()


class DropDirectoryScanner:
    """Scans source directories for documents and produces chunked JSON."""

    def __init__(self, source_dirs: List[Path], output_dir: Path):
        self.source_dirs = source_dirs
        self.output_dir = output_dir

    def discover_files(self) -> List[Tuple[Path, Path]]:
        """Discover supported files across all source dirs.

        Returns list of (absolute_path, source_dir) so we can compute
        relative paths per source directory.
        """
        results: List[Tuple[Path, Path]] = []
        for src_dir in self.source_dirs:
            if not src_dir.is_dir():
                logger.debug(f"Source directory does not exist: {src_dir}")
                continue
            for ext in sorted(SUPPORTED_EXTENSIONS):
                for filepath in sorted(src_dir.rglob(f"*{ext}")):
                    if filepath.is_file():
                        results.append((filepath, src_dir))
        return results

    def chunk_file(self, filepath: Path, source_dir: Path) -> List[Dict]:
        """Read and chunk a single file. Returns list of chunk dicts."""
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Cannot read {filepath}: {e}")
            return []

        relative_path = str(filepath.relative_to(source_dir))
        doc_type = _classify_document_type(filepath)
        suffix = filepath.suffix.lower()

        # Choose chunking strategy
        if suffix == ".md":
            raw_chunks = _chunk_markdown(content)
        elif suffix in (".yml", ".yaml"):
            raw_chunks = _chunk_whole_file(content, filepath.name)
        else:
            # .rst and .txt
            raw_chunks = _chunk_by_paragraphs(content)

        chunks: List[Dict] = []
        for i, (title, section_content) in enumerate(raw_chunks):
            if len(section_content.strip()) < MIN_CHUNK_LENGTH:
                continue

            chunk_title = title or filepath.stem
            cid = _chunk_id(relative_path, i, chunk_title)

            chunks.append(
                {
                    "id": cid,
                    "source_file": relative_path,
                    "title": chunk_title,
                    "content": section_content.strip(),
                    "chunk_type": suffix.lstrip("."),
                    "metadata": {
                        "source_file": relative_path,
                        "document_type": doc_type,
                        "section_index": i,
                        "word_count": len(section_content.split()),
                        "created_at": datetime.now().isoformat(),
                    },
                    "word_count": len(section_content.split()),
                    "created_at": datetime.now().isoformat(),
                }
            )

        return chunks

    def scan_and_process(self) -> Tuple[int, int]:
        """Scan all source dirs, chunk files, and write document_chunks.json.

        Returns:
            (files_processed, chunks_generated)
        """
        discovered = self.discover_files()
        logger.info(f"Discovered {len(discovered)} files across {len(self.source_dirs)} source dirs")

        all_chunks: List[Dict] = []
        files_processed = 0

        for filepath, source_dir in discovered:
            chunks = self.chunk_file(filepath, source_dir)
            if chunks:
                all_chunks.extend(chunks)
                files_processed += 1

        # Write output
        self.output_dir.mkdir(parents=True, exist_ok=True)
        chunks_file = self.output_dir / "document_chunks.json"

        with open(chunks_file, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)

        logger.info(f"Wrote {len(all_chunks)} chunks from {files_processed} files to {chunks_file}")
        return files_processed, len(all_chunks)
