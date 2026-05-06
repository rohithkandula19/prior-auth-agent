"""Parse a policy PDF into a single text blob with page markers preserved.

We use pdfplumber for layout-aware extraction and emit [[PAGE n]] markers so
the criteria extractor can assign page numbers and downstream code can map
char spans back to pages.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class ParsedPolicy:
    raw_text: str
    page_offsets: list[tuple[int, int]]  # (start, end) char span per page, 1-indexed


def parse_pdf(path: str | Path) -> ParsedPolicy:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Policy PDF not found: {path}")

    parts: list[str] = []
    page_offsets: list[tuple[int, int]] = []
    cursor = 0

    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            header = f"[[PAGE {i}]]\n"
            text = page.extract_text() or ""
            text = text.strip() + "\n"
            block = header + text
            parts.append(block)
            page_offsets.append((cursor, cursor + len(block)))
            cursor += len(block)

    raw_text = "".join(parts)
    log.info("policy_parsed", path=str(path), pages=len(page_offsets), chars=len(raw_text))
    return ParsedPolicy(raw_text=raw_text, page_offsets=page_offsets)


def parse_text(text: str) -> ParsedPolicy:
    """Helper for tests and synthetic policies. Treats input as a single page."""
    block = "[[PAGE 1]]\n" + text.strip() + "\n"
    return ParsedPolicy(raw_text=block, page_offsets=[(0, len(block))])
