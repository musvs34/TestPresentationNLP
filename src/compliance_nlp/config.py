"""Configuration loaders for the compliance NLP POC."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


VALID_ALERT_LEVELS = {"interdit", "alerte", "ambigue"}
DEFAULT_FORBIDDEN_WORDS_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "forbidden_words.csv"
)
DEFAULT_ARTICLE9_TERMS_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "article9_terms.csv"
)
DEFAULT_ARTICLE9_WHITELIST_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "article9_whitelist.csv"
)


@dataclass(frozen=True, slots=True)
class ForbiddenTerm:
    """A forbidden term and its configured alert level."""

    term: str
    alert_level: str


@dataclass(frozen=True, slots=True)
class Article9Term:
    """A sensitive Article 9 rule configured by compliance teams."""

    rule_id: str
    category: str
    label: str
    terms: tuple[str, ...]
    synonyms: tuple[str, ...]
    alert_level: str
    base_score: float
    fuzzy_threshold: float

    @property
    def all_terms(self) -> tuple[str, ...]:
        return self.terms + self.synonyms


@dataclass(frozen=True, slots=True)
class WhitelistTerm:
    """A configured expression that suppresses sensitive findings."""

    expression: str
    reason: str


def load_forbidden_terms(csv_path: str | Path | None = None) -> list[ForbiddenTerm]:
    """Load forbidden terms from the project CSV file."""

    path = Path(csv_path) if csv_path is not None else DEFAULT_FORBIDDEN_WORDS_PATH
    if not path.exists():
        return []

    terms: list[ForbiddenTerm] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            term = (row.get("mot_interdit") or "").strip()
            alert_level = (row.get("niveau_alerte") or "").strip().lower()

            if not term:
                continue
            if alert_level not in VALID_ALERT_LEVELS:
                raise ValueError(
                    f"Invalid alert level '{alert_level}' for forbidden term '{term}'."
                )

            terms.append(ForbiddenTerm(term=term.lower(), alert_level=alert_level))

    return terms


def _split_pipe_values(raw_value: str | None) -> tuple[str, ...]:
    if not raw_value:
        return ()
    return tuple(value.strip().lower() for value in raw_value.split("|") if value.strip())


def load_article9_terms(csv_path: str | Path | None = None) -> list[Article9Term]:
    """Load configured Article 9 sensitive data rules."""

    path = Path(csv_path) if csv_path is not None else DEFAULT_ARTICLE9_TERMS_PATH
    if not path.exists():
        return []

    terms: list[Article9Term] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rule_id = (row.get("rule_id") or "").strip()
            category = (row.get("category") or "").strip().lower()
            label = (row.get("label") or rule_id).strip()
            configured_terms = _split_pipe_values(row.get("terms"))
            synonyms = _split_pipe_values(row.get("synonyms"))
            alert_level = (row.get("alert_level") or "interdit").strip().lower()
            base_score = float((row.get("base_score") or "0.8").strip())
            fuzzy_threshold = float((row.get("fuzzy_threshold") or "0.88").strip())

            if not rule_id or not category or not configured_terms:
                continue
            if alert_level not in VALID_ALERT_LEVELS:
                raise ValueError(
                    f"Invalid alert level '{alert_level}' for Article 9 rule '{rule_id}'."
                )
            if not 0 <= base_score <= 1:
                raise ValueError(f"Invalid base score for Article 9 rule '{rule_id}'.")
            if not 0 <= fuzzy_threshold <= 1:
                raise ValueError(
                    f"Invalid fuzzy threshold for Article 9 rule '{rule_id}'."
                )

            terms.append(
                Article9Term(
                    rule_id=rule_id,
                    category=category,
                    label=label,
                    terms=configured_terms,
                    synonyms=synonyms,
                    alert_level=alert_level,
                    base_score=base_score,
                    fuzzy_threshold=fuzzy_threshold,
                )
            )

    return terms


def load_whitelist_terms(csv_path: str | Path | None = None) -> list[WhitelistTerm]:
    """Load expressions that should suppress Article 9 findings."""

    path = Path(csv_path) if csv_path is not None else DEFAULT_ARTICLE9_WHITELIST_PATH
    if not path.exists():
        return []

    terms: list[WhitelistTerm] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            expression = (row.get("expression") or "").strip().lower()
            reason = (row.get("reason") or "").strip()
            if expression:
                terms.append(WhitelistTerm(expression=expression, reason=reason))

    return terms
