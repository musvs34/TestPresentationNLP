"""spaCy-based linguistic detectors for configured compliance rules."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import DEFAULT_SPACY_SYNONYMS_PATH, GenericDetectionRule, WhitelistTerm, load_spacy_synonym_map
from .models import Finding
from .text_utils import compact_text, normalize_for_matching, shorten


DEFAULT_MODEL_STORE_DIR = Path(os.environ.get("COMPLIANCE_NLP_MODEL_STORE", r"D:\Workspaces\modelStore"))
DEFAULT_SPACY_MODEL = str(DEFAULT_MODEL_STORE_DIR / "fr_core_news_md")
DEFAULT_SPACY_SYNONYMS_FILE = str(DEFAULT_SPACY_SYNONYMS_PATH)


@dataclass(frozen=True, slots=True)
class LinguisticMatch:
    """Internal spaCy match candidate before it is turned into a Finding."""

    configured_term: str
    matched_text: str
    detection_type: str
    score: float


@lru_cache(maxsize=4)
def load_spacy_model(model_name: str = DEFAULT_SPACY_MODEL):  # type: ignore[no-untyped-def]
    """Load and cache the configured French spaCy pipeline."""

    try:
        import spacy
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "The spaCy branch requires the 'spacy' package. Install optional NLP "
            "dependencies before enabling it."
        ) from exc

    try:
        return spacy.load(model_name)
    except OSError as exc:  # pragma: no cover - depends on optional model
        raise RuntimeError(
            f"The spaCy branch requires the French model '{model_name}'. "
            "Install it before enabling the branch."
        ) from exc


def _score(base_score: float, modifier: float) -> float:
    return round(max(0.0, min(1.0, base_score + modifier)), 2)


def _word_pattern(term: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", flags=re.IGNORECASE)


def _simple_french_stem(token: str) -> str:
    for suffix in ("iques", "ique", "euses", "euse", "ments", "ment", "es", "s", "e"):
        if len(token) > len(suffix) + 4 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _looks_like_same_root(configured: str, token: str) -> bool:
    configured_stem = _simple_french_stem(configured)
    token_stem = _simple_french_stem(token)
    if len(configured_stem) < 5 or len(token_stem) < 5:
        return False
    return configured_stem == token_stem


def _iter_ngrams(items: list[Any], size: int) -> list[list[Any]]:
    return [items[index : index + size] for index in range(len(items) - size + 1)]


def _token_text(token: Any) -> str:
    return normalize_for_matching(token.text)


def _token_lemma(token: Any) -> str:
    lemma = token.lemma_ if getattr(token, "lemma_", "") else token.text
    if lemma == "-PRON-":
        lemma = token.text
    return normalize_for_matching(lemma)


def _content_tokens(doc: Any) -> list[Any]:
    return [
        token
        for token in doc
        if not token.is_space and not token.is_punct and normalize_for_matching(token.text)
    ]


def _phrase_tokens(nlp: Any, phrase: str) -> list[Any]:
    return _content_tokens(nlp(phrase))


def _surface_text(tokens: list[Any]) -> str:
    return normalize_for_matching(" ".join(token.text for token in tokens))


def _lemma_text(tokens: list[Any]) -> str:
    return " ".join(_token_lemma(token) for token in tokens)


def _is_whitelisted(matched_text: str, section_text: str, whitelist: list[WhitelistTerm]) -> bool:
    normalized_match = normalize_for_matching(matched_text)
    normalized_section = normalize_for_matching(section_text)

    for item in whitelist:
        normalized_expression = normalize_for_matching(item.expression)
        if normalized_expression not in normalized_section:
            continue
        if normalized_match in normalized_expression or normalized_expression in normalized_match:
            return True

    return False


def _find_exact_match(
    normalized_section: str,
    configured_term: str,
    is_synonym: bool,
    base_score: float,
) -> LinguisticMatch | None:
    normalized_term = normalize_for_matching(configured_term)
    if not _word_pattern(normalized_term).search(normalized_section):
        return None

    return LinguisticMatch(
        configured_term=configured_term,
        matched_text=configured_term,
        detection_type="synonym" if is_synonym else "exact",
        score=_score(base_score, -0.04 if is_synonym else 0.0),
    )


def _find_lemma_match(
    tokens: list[Any],
    configured_term: str,
    nlp: Any,
    base_score: float,
) -> LinguisticMatch | None:
    term_tokens = _phrase_tokens(nlp, configured_term)
    if not term_tokens:
        return None

    normalized_term = normalize_for_matching(configured_term)
    term_lemmas = _lemma_text(term_tokens)

    for candidate in _iter_ngrams(tokens, len(term_tokens)):
        candidate_surface = _surface_text(candidate)
        if candidate_surface == normalized_term:
            continue
        if _lemma_text(candidate) == term_lemmas:
            return LinguisticMatch(
                configured_term=configured_term,
                matched_text=candidate_surface,
                detection_type="lemma",
                score=_score(base_score, -0.07),
            )

    return None


def _find_root_match(
    tokens: list[Any],
    configured_term: str,
    nlp: Any,
    base_score: float,
) -> LinguisticMatch | None:
    term_tokens = _phrase_tokens(nlp, configured_term)
    if len(term_tokens) != 1:
        return None

    term_root = _token_lemma(term_tokens[0])
    for token in tokens:
        candidate = _token_lemma(token)
        if candidate == term_root:
            continue
        if _looks_like_same_root(term_root, candidate):
            return LinguisticMatch(
                configured_term=configured_term,
                matched_text=_token_text(token),
                detection_type="root",
                score=_score(base_score, -0.10),
            )

    return None


def _find_fuzzy_match(
    tokens: list[Any],
    configured_term: str,
    nlp: Any,
    base_score: float,
    threshold: float,
) -> LinguisticMatch | None:
    term_tokens = _phrase_tokens(nlp, configured_term)
    if not term_tokens:
        return None

    normalized_term = normalize_for_matching(configured_term)
    best_candidate = ""
    best_ratio = 0.0
    for candidate_tokens in _iter_ngrams(tokens, len(term_tokens)):
        candidate = _surface_text(candidate_tokens)
        if candidate == normalized_term:
            continue
        ratio = SequenceMatcher(None, normalized_term, candidate).ratio()
        if ratio > best_ratio:
            best_candidate = candidate
            best_ratio = ratio

    if best_ratio < threshold:
        return None

    return LinguisticMatch(
        configured_term=configured_term,
        matched_text=best_candidate,
        detection_type="fuzzy",
        score=_score(base_score, -0.16),
    )


def _pick_best(
    current: LinguisticMatch | None,
    candidates: list[LinguisticMatch | None],
) -> LinguisticMatch | None:
    valid_candidates = [candidate for candidate in candidates if candidate is not None]
    if current is not None:
        valid_candidates.append(current)
    if not valid_candidates:
        return None
    return max(valid_candidates, key=lambda candidate: candidate.score)


@lru_cache(maxsize=8)
def load_linguistic_synonym_map(
    synonyms_path: str = DEFAULT_SPACY_SYNONYMS_FILE,
) -> dict[str, tuple[str, ...]]:
    """Load synonym candidates used by the spaCy branch."""

    return load_spacy_synonym_map(synonyms_path)


def _synonyms_for_rule_terms(
    rule: GenericDetectionRule,
    synonym_map: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    """Resolve proposed synonyms from the rule's forbidden terms only."""

    rule_terms = {normalize_for_matching(term) for term in rule.terms}
    seen: set[str] = set()
    resolved: list[str] = []

    for term in rule.terms:
        normalized_term = normalize_for_matching(term)
        for synonym in synonym_map.get(normalized_term, ()):
            normalized_synonym = normalize_for_matching(synonym)
            if not normalized_synonym or normalized_synonym in rule_terms or normalized_synonym in seen:
                continue
            seen.add(normalized_synonym)
            resolved.append(normalized_synonym)

    return tuple(resolved)


def _best_match_for_rule(
    section_text: str,
    rule: GenericDetectionRule,
    nlp: Any,
    synonym_map: dict[str, tuple[str, ...]],
) -> LinguisticMatch | None:
    doc = nlp(section_text)
    tokens = _content_tokens(doc)
    normalized_section = normalize_for_matching(section_text)
    best_match: LinguisticMatch | None = None

    for configured_term in rule.terms:
        candidates = [
            _find_exact_match(normalized_section, configured_term, False, rule.base_score),
            _find_lemma_match(tokens, configured_term, nlp, rule.base_score),
            _find_root_match(tokens, configured_term, nlp, rule.base_score),
            _find_fuzzy_match(tokens, configured_term, nlp, rule.base_score, rule.fuzzy_threshold),
        ]
        best_match = _pick_best(best_match, candidates)

    for synonym in _synonyms_for_rule_terms(rule, synonym_map):
        candidates = [
            _find_exact_match(normalized_section, synonym, True, rule.base_score),
            _find_lemma_match(tokens, synonym, nlp, _score(rule.base_score, -0.04)),
            _find_root_match(tokens, synonym, nlp, _score(rule.base_score, -0.04)),
            _find_fuzzy_match(tokens, synonym, nlp, rule.base_score, rule.fuzzy_threshold),
        ]
        best_match = _pick_best(best_match, candidates)

    return best_match


def analyze_linguistic_section(
    section_name: str,
    section_text: str,
    generic_rules: list[GenericDetectionRule],
    whitelist_terms: list[WhitelistTerm] | None = None,
    nlp: Any | None = None,
    spacy_model: str = DEFAULT_SPACY_MODEL,
    spacy_synonyms_path: str = DEFAULT_SPACY_SYNONYMS_FILE,
    synonym_map: dict[str, tuple[str, ...]] | None = None,
) -> list[Finding]:
    """Apply the optional spaCy branch to one section."""

    findings: list[Finding] = []
    compact_section = compact_text(section_text)
    if not compact_section:
        return findings

    nlp = nlp or load_spacy_model(spacy_model)
    synonym_map = synonym_map if synonym_map is not None else load_linguistic_synonym_map(spacy_synonyms_path)
    scoped_rules = [
        rule for rule in generic_rules if section_name in rule.section_scope or "*" in rule.section_scope
    ]

    whitelist_terms = whitelist_terms or []
    for rule in scoped_rules:
        match = _best_match_for_rule(compact_section, rule, nlp, synonym_map)
        if match is None:
            continue
        if rule.applies_whitelist and _is_whitelisted(
            match.matched_text,
            compact_section,
            whitelist_terms,
        ):
            continue

        code = f"article9_{rule.category}" if rule.rule_scope == "article9" else rule.rule_id

        findings.append(
            Finding(
                code=code,
                severity=rule.severity,
                section=section_name,
                title=rule.label,
                detail=(
                    f"Rule '{rule.rule_id}' detected '{match.matched_text}' "
                    f"as {match.detection_type} with spaCy."
                ),
                evidence=shorten(compact_section),
                matched_term=match.matched_text,
                alert_level=rule.alert_level,
                category=rule.category,
                score=match.score,
                branch_score=match.score,
                spacy_score=match.score,
                detection_type=match.detection_type,
                detection_engine="spacy",
                rule_id=rule.rule_id,
                rule_scope=rule.rule_scope,
                regulatory_family=rule.regulatory_family,
            )
        )

    return findings


def analyze_linguistic_sections(
    sections: dict[str, str],
    generic_rules: list[GenericDetectionRule],
    whitelist_terms: list[WhitelistTerm] | None = None,
    spacy_model: str = DEFAULT_SPACY_MODEL,
    spacy_synonyms_path: str = DEFAULT_SPACY_SYNONYMS_FILE,
) -> list[Finding]:
    """Apply the optional spaCy branch to all available sections."""

    nlp = load_spacy_model(spacy_model)
    synonym_map = load_linguistic_synonym_map(spacy_synonyms_path)
    findings: list[Finding] = []
    for section_name, section_text in sections.items():
        findings.extend(
            analyze_linguistic_section(
                section_name,
                section_text,
                generic_rules,
                whitelist_terms=whitelist_terms,
                nlp=nlp,
                spacy_model=spacy_model,
                spacy_synonyms_path=spacy_synonyms_path,
                synonym_map=synonym_map,
            )
        )
    return findings
