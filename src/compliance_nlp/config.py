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
DEFAULT_SECTIONS_PATH = Path(__file__).resolve().parents[2] / "configs" / "sections.csv"
DEFAULT_GENERIC_RULES_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "generic_detection_rules.csv"
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


@dataclass(frozen=True, slots=True)
class SectionDefinition:
    """A configured text section to extract before applying controls."""

    section_id: str
    label: str
    start_marker: str
    end_marker: str | None = None


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


def _parse_bool(raw_value: str | None, default: bool = False) -> bool:
    if raw_value is None or not raw_value.strip():
        return default
    return raw_value.strip().casefold() in {"1", "true", "yes", "oui", "y"}


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


def load_section_definitions(csv_path: str | Path | None = None) -> list[SectionDefinition]:
    """Load configured document sections."""

    path = Path(csv_path) if csv_path is not None else DEFAULT_SECTIONS_PATH
    if not path.exists():
        return []

    sections: list[SectionDefinition] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            section_id = (row.get("section_id") or "").strip().lower()
            label = (row.get("label") or section_id).strip()
            start_marker = (row.get("start_marker") or "").strip()
            end_marker = (row.get("end_marker") or "").strip() or None
            if not section_id:
                continue
            sections.append(
                SectionDefinition(
                    section_id=section_id,
                    label=label,
                    start_marker=start_marker,
                    end_marker=end_marker,
                )
            )

    return sections


def load_generic_detection_rules(
    csv_path: str | Path | None = None,
) -> list[GenericDetectionRule]:
    """Load generic configured detection rules."""

    path = Path(csv_path) if csv_path is not None else DEFAULT_GENERIC_RULES_PATH
    if not path.exists():
        return []

    rules: list[GenericDetectionRule] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
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


def article9_terms_to_generic_rules(
    article9_terms: list[Article9Term],
) -> list[GenericDetectionRule]:
    """Convert legacy Article 9 rules to the central configured-rule model."""

    return [
        GenericDetectionRule(
            rule_id=term.rule_id,
            rule_scope="article9",
            regulatory_family="rgpd_article_9",
            section_scope=("document",),
            category=term.category,
            label=term.label,
            terms=term.terms,
            synonyms=term.synonyms,
            alert_level=term.alert_level,
            severity="critical",
            base_score=term.base_score,
            fuzzy_threshold=term.fuzzy_threshold,
            applies_whitelist=True,
        )
        for term in article9_terms
    ]
