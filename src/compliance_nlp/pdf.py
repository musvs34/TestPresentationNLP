"""PDF extraction utilities."""

from __future__ import annotations

from pathlib import Path


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract text from a PDF using pypdf."""

    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "pypdf is required to read PDF inputs. Install project dependencies first."
        ) from exc

    path = Path(pdf_path)
    reader = PdfReader(str(path))

    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")

    return "\n".join(pages).strip()
