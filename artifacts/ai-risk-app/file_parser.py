"""Parse minutes from various file formats."""
from __future__ import annotations

from pathlib import Path


def parse_file(file_path: str, filename: str) -> str:
    """Extract plain text from docx, pdf, or txt file."""
    suffix = Path(filename).suffix.lower()

    if suffix in (".docx", ".doc"):
        return _parse_docx(file_path)
    elif suffix == ".pdf":
        return _parse_pdf(file_path)
    else:
        return _parse_text(file_path)


def _parse_docx(file_path: str) -> str:
    from docx import Document
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _parse_pdf(file_path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(file_path)
    texts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            texts.append(t)
    return "\n".join(texts)


def _parse_text(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()
