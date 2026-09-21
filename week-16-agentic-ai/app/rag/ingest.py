from __future__ import annotations

import re
from pathlib import Path
from typing import List


def load_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader  # local import: avoid requiring pypdf for .txt/.md-only use

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type: {suffix}")


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> List[str]:
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = re.sub(r"[ \t]+\n", "\n", text).strip()
    if not text:
        return []

    separators = ["\n\n", "\n", ". ", " "]

    def split(segment: str, seps: List[str]) -> List[str]:
        if len(segment) <= chunk_size:
            return [segment] if segment.strip() else []
        if not seps:
            return [segment[i : i + chunk_size] for i in range(0, len(segment), chunk_size)]
        sep, rest = seps[0], seps[1:]
        parts = segment.split(sep)
        chunks: List[str] = []
        buffer = ""
        for part in parts:
            candidate = (buffer + sep + part) if buffer else part
            if len(candidate) <= chunk_size:
                buffer = candidate
            else:
                if buffer:
                    chunks.extend(split(buffer, rest))
                buffer = part
        if buffer:
            chunks.extend(split(buffer, rest))
        return chunks

    raw_chunks = [c.strip() for c in split(text, separators) if c.strip()]

    overlapped: List[str] = []
    for i, chunk in enumerate(raw_chunks):
        if i == 0:
            overlapped.append(chunk)
            continue
        prev_tail = raw_chunks[i - 1][-overlap:]
        overlapped.append((prev_tail + " " + chunk).strip())
    return overlapped
