"""Configuration loaders for the compliance NLP POC."""

from __future__ import annotations

import csv
import html
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import urlopen


VALID_ALERT_LEVELS = {"interdit", "alerte", "ambigue"}
DEFAULT_ARTICLE9_WHITELIST_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "article9_whitelist.csv"
)
DEFAULT_GENERIC_RULES_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "Mots_interdits.csv"
)
DEFAULT_SPACY_SYNONYMS_PATH = Path(__file__).resolve().parents[2] / "configs" / "spacy_synonyms.csv"
DEFAULT_MODEL_STORE_DIR = Path(os.environ.get("COMPLIANCE_NLP_MODEL_STORE", r"E:\Workspace\modelStore"))
DEFAULT_JEUXDEMOTS_STORE_PATH = DEFAULT_MODEL_STORE_DIR / "jeuxdemots"
JEUXDEMOTS_SYNONYM_RELATION_ID = 5


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


def _normalize_term_key(raw_value: str) -> str:
    normalized = unicodedata.normalize("NFKD", raw_value)
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", ascii_text.casefold()).strip()


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


def _clean_jeuxdemots_term(raw_value: str) -> str:
    term = html.unescape(raw_value).strip()
    term = term.split(">", 1)[0].strip()
    if term.casefold().startswith("en:"):
        return ""
    if not term or ";" in term:
        return ""
    return _normalize_term_key(term)


def _parse_jeuxdemots_synonyms(
    dump_text: str,
    source_term: str,
    max_synonyms: int = 5,
    min_weight: int = 25,
) -> tuple[str, ...]:
    entries: dict[int, str] = {}
    source_eid: int | None = None
    relations: list[tuple[int, int]] = []
    normalized_source = _normalize_term_key(source_term)

    source_match = re.search(r"\(eid=(\d+)\)", dump_text)
    if source_match:
        source_eid = int(source_match.group(1))

    for line in dump_text.splitlines():
        line = html.unescape(re.sub(r"<[^>]+>", "", line)).strip()
        entry_match = re.match(r"e;(\d+);'([^']+)';", line)
        if entry_match:
            eid = int(entry_match.group(1))
            cleaned_term = _clean_jeuxdemots_term(entry_match.group(2))
            if cleaned_term:
                entries[eid] = cleaned_term
            continue

        relation_match = re.match(r"r;\d+;(\d+);(\d+);5;(-?\d+);", line)
        if not relation_match:
            continue
        node1 = int(relation_match.group(1))
        node2 = int(relation_match.group(2))
        weight = int(relation_match.group(3))
        if weight < min_weight:
            continue
        if source_eid is not None and node1 != source_eid:
            continue
        relations.append((weight, node2))

    synonyms: list[str] = []
    seen: set[str] = {normalized_source}
    for _, target_id in sorted(relations, reverse=True):
        synonym = entries.get(target_id)
        if not synonym or synonym in seen:
            continue
        seen.add(synonym)
        synonyms.append(synonym)
        if len(synonyms) >= max_synonyms:
            break

    return tuple(synonyms)


def _load_jeuxdemots_dump(
    term: str,
    store_path: Path,
    allow_network: bool = True,
) -> str:
    normalized_term = _normalize_term_key(term)
    cache_path = store_path / f"{_slugify(normalized_term, 'term')}.html"
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")
    if not allow_network:
        return ""

    store_path.mkdir(parents=True, exist_ok=True)
    url = (
        "http://www.jeuxdemots.org/rezo-dump.php"
        f"?gotermsubmit=Chercher&gotermrel={quote_plus(normalized_term)}"
        f"&rel={JEUXDEMOTS_SYNONYM_RELATION_ID}"
    )
    with urlopen(url, timeout=20) as response:
        payload = response.read()
    dump_text = payload.decode("iso-8859-1", errors="replace")
    cache_path.write_text(dump_text, encoding="utf-8")
    return dump_text


def _load_jeuxdemots_synonyms(
    term: str,
    store_path: Path,
    allow_network: bool = True,
    max_synonyms: int = 5,
    min_weight: int = 25,
) -> tuple[str, ...]:
    try:
        dump_text = _load_jeuxdemots_dump(
            term,
            store_path=store_path,
            allow_network=allow_network,
        )
    except OSError:
        return ()
    if not dump_text:
        return ()
    return _parse_jeuxdemots_synonyms(
        dump_text,
        term,
        max_synonyms=max_synonyms,
        min_weight=min_weight,
    )


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
            term = _normalize_term_key(row.get("term") or "")
            synonyms = _split_pipe_values(row.get("synonyms") or row.get("proposed_synonyms"))
            if term and synonyms:
                synonym_map[term] = synonyms

    return synonym_map


def refresh_spacy_synonyms_from_forbidden_words(
    forbidden_words_path: str | Path | None = None,
    synonyms_path: str | Path | None = None,
    jeuxdemots_store_path: str | Path | None = None,
    enrich_with_jeuxdemots: bool = False,
    allow_network: bool = True,
    max_synonyms: int = 5,
    min_weight: int = 25,
) -> int:
    """Regenerate the spaCy synonym CSV from the forbidden words list.

    Existing synonym values are preserved when their normalized term still exists
    in the forbidden words file. Terms not present in the forbidden words file
    are removed from the generated synonym CSV. When requested, JeuxDeMots
    synonym relations are used to fill missing synonym values.
    """

    source_path = Path(forbidden_words_path) if forbidden_words_path is not None else DEFAULT_GENERIC_RULES_PATH
    target_path = Path(synonyms_path) if synonyms_path is not None else DEFAULT_SPACY_SYNONYMS_PATH
    store_path = (
        Path(jeuxdemots_store_path)
        if jeuxdemots_store_path is not None
        else DEFAULT_JEUXDEMOTS_STORE_PATH
    )

    existing_synonyms = load_spacy_synonym_map(target_path)
    terms: list[str] = []
    seen: set[str] = set()

    if not source_path.exists():
        return 0

    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = _csv_reader(handle)
        for row in reader:
            raw_term = (row.get("Terme interdit") or "").strip()
            normalized_term = _normalize_term_key(raw_term)
            if not normalized_term or normalized_term in seen:
                continue
            seen.add(normalized_term)
            terms.append(normalized_term)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["term", "synonyms"])
        writer.writeheader()
        for term in terms:
            synonyms = existing_synonyms.get(term, ())
            if enrich_with_jeuxdemots and not synonyms:
                synonyms = _load_jeuxdemots_synonyms(
                    term,
                    store_path=store_path,
                    allow_network=allow_network,
                    max_synonyms=max_synonyms,
                    min_weight=min_weight,
                )
            writer.writerow(
                {
                    "term": term,
                    "synonyms": "|".join(synonyms),
                }
            )

    return len(terms)


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
