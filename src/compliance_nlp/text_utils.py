"""Text normalization and section extraction helpers."""

from __future__ import annotations

import re
import unicodedata


def normalize_whitespace(text: str) -> str:
    """Normalize line breaks and repeated whitespace."""

    compact = text.replace("\r", "\n")
    compact = re.sub(r"[ \t]+", " ", compact)
    compact = re.sub(r"\n{2,}", "\n", compact)
    return compact.strip()


def compact_text(text: str) -> str:
    """Build a single-line representation for pattern matching."""

    return re.sub(r"\s+", " ", text).strip()


def normalize_for_matching(text: str) -> str:
    """Normalize text for accent-insensitive and case-insensitive matching."""

    without_accents = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(
        character for character in without_accents if not unicodedata.combining(character)
    )
    lowered = ascii_text.casefold()
    return re.sub(r"\s+", " ", lowered).strip()


def tokenize_words(text: str) -> list[str]:
    """Return normalized word tokens used by fuzzy detectors."""

    normalized = normalize_for_matching(text)
    return re.findall(r"\b[\w']+\b", normalized)


def shorten(text: str, max_length: int = 220) -> str:
    """Shorten evidence snippets for result payloads."""

    compact = compact_text(text)
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 3].rstrip() + "..."
