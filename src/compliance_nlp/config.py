"""Configuration loaders for the compliance NLP POC."""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


VALID_ALERT_LEVELS = {"interdit", "alerte", "ambigue"}
DEFAULT_ARTICLE9_WHITELIST_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "article9_whitelist.csv"
)
DEFAULT_GENERIC_RULES_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "Mots_interdits.csv"
)
DEFAULT_SPACY_SYNONYMS_PATH = Path(__file__).resolve().parents[2] / "configs" / "spacy_synonyms.csv"


@dataclass(frozen=True, slots=True)
class WhitelistTerm:
    """A configured expression that suppresses sensitive findings."""

    expression: str
    reason: str


@dataclass(frozen=True, slots=True)
class GenericDetectionRule:
    """A generic configured rule for section and wording controls."""

    rule_id: str
    rule_scope: str
    regulatory_family: str
    section_scope: tuple[str, ...]
    category: str
    label: str
    terms: tuple[str, ...]
    synonyms: tuple[str, ...]
    alert_level: str
    severity: str
    base_score: float
    fuzzy_threshold: float
    applies_whitelist: bool = False

    @property
    def all_terms(self) -> tuple[str, ...]:
        return self.terms + self.synonyms


def _split_pipe_values(raw_value: str | None) -> tuple[str, ...]:
    if not raw_value:
        return ()
    return tuple(value.strip().lower() for value in raw_value.split("|") if value.strip())


def _slugify(raw_value: str, default: str = "general") -> str:
    normalized = unicodedata.normalize("NFKD", raw_value)
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_text.casefold()).strip("_")
    return slug or default


def _parse_bool(raw_value: str | None, default: bool = False) -> bool:
    if raw_value is None or not raw_value.strip():
        return default
    return raw_value.strip().casefold() in {"1", "true", "yes", "oui", "y"}


def _csv_reader(handle) -> csv.DictReader:
    sample = handle.read(2048)
    handle.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
    except csv.Error:
        dialect = csv.excel
    return csv.DictReader(handle, dialect=dialect)


def load_whitelist_terms(csv_path: str | Path | None = None) -> list[WhitelistTerm]:
    """Load expressions that should suppress Article 9 findings."""

    path = Path(csv_path) if csv_path is not None else DEFAULT_ARTICLE9_WHITELIST_PATH
    if not path.exists():
        return []

    terms: list[WhitelistTerm] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = _csv_reader(handle)
        for row in reader:
            expression = (row.get("expression") or "").strip().lower()
            reason = (row.get("reason") or "").strip()
            if expression:
                terms.append(WhitelistTerm(expression=expression, reason=reason))

    return terms


def load_spacy_synonym_map(csv_path: str | Path | None = None) -> dict[str, tuple[str, ...]]:
    """Load proposed synonym candidates for the spaCy branch."""

    path = Path(csv_path) if csv_path is not None else DEFAULT_SPACY_SYNONYMS_PATH
    if not path.exists():
        return {}

    synonym_map: dict[str, tuple[str, ...]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = _csv_reader(handle)
        for row in reader:
            term = (row.get("term") or "").strip().lower()
            synonyms = _split_pipe_values(row.get("synonyms") or row.get("proposed_synonyms"))
            if term and synonyms:
                synonym_map[term] = synonyms

    return synonym_map


def load_generic_detection_rules(
    csv_path: str | Path | None = None,
) -> list[GenericDetectionRule]:
    """Load generic configured detection rules.

    Supports both the historical technical format and the DPO word-list format:
    Catégorie;Terme interdit;Justification.
    """

    path = Path(csv_path) if csv_path is not None else DEFAULT_GENERIC_RULES_PATH
    if not path.exists():
        return []

    rules: list[GenericDetectionRule] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = _csv_reader(handle)
        for index, row in enumerate(reader, start=1):
            is_forbidden_words_format = "Terme interdit" in row

            if is_forbidden_words_format:
                term = (row.get("Terme interdit") or "").strip()
                raw_category = (row.get("Catégorie") or "general").strip()
                justification = (row.get("Justification") or raw_category).strip()
                category_slug = _slugify(raw_category)
                category = category_slug
                rule_id = f"mots_interdits_{index:03d}_{_slugify(term, 'terme')}"
                is_article9 = "article 9" in raw_category.casefold()
                rule_scope = "article9" if is_article9 else "general"
                regulatory_family = "rgpd_article_9" if is_article9 else category_slug
                section_scope = ("document",)
                label = justification
                terms = (term,) if term else ()
                synonyms = ()
                alert_level = "interdit"
                severity = "critical" if is_article9 else "high"
                base_score = 0.90 if is_article9 else 0.85
                fuzzy_threshold = 0.88
                applies_whitelist = is_article9
            else:
                rule_id = (row.get("rule_id") or "").strip()
                rule_scope = (row.get("rule_scope") or row.get("scope") or "general").strip().lower()
                regulatory_family = (
                    row.get("regulatory_family") or rule_scope or "general"
                ).strip().lower()
                section_scope = _split_pipe_values(row.get("section_scope"))
                category = (row.get("category") or "").strip().lower()
                label = (row.get("label") or rule_id).strip()
                terms = _split_pipe_values(row.get("terms"))
                synonyms = _split_pipe_values(row.get("synonyms"))
                alert_level = (row.get("alert_level") or "alerte").strip().lower()
                severity = (row.get("severity") or "medium").strip().lower()
                base_score = float((row.get("base_score") or "0.75").strip())
                fuzzy_threshold = float((row.get("fuzzy_threshold") or "0.88").strip())
                applies_whitelist = _parse_bool(
                    row.get("applies_whitelist"),
                    default=rule_scope == "article9",
                )

            if not rule_id or not section_scope or not category or not terms:
                continue
            if alert_level not in VALID_ALERT_LEVELS:
                raise ValueError(
                    f"Invalid alert level '{alert_level}' for generic rule '{rule_id}'."
                )
            if not 0 <= base_score <= 1:
                raise ValueError(f"Invalid base score for generic rule '{rule_id}'.")
            if not 0 <= fuzzy_threshold <= 1:
                raise ValueError(
                    f"Invalid fuzzy threshold for generic rule '{rule_id}'."
                )

            rules.append(
                GenericDetectionRule(
                    rule_id=rule_id,
                    rule_scope=rule_scope,
                    regulatory_family=regulatory_family,
                    section_scope=section_scope,
                    category=category,
                    label=label,
                    terms=terms,
                    synonyms=synonyms,
                    alert_level=alert_level,
                    severity=severity,
                    base_score=base_score,
                    fuzzy_threshold=fuzzy_threshold,
                    applies_whitelist=applies_whitelist,
                )
            )

    return rules
