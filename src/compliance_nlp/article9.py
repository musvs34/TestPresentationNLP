"""Article 9 GDPR sensitive-data detectors."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from .config import Article9Term, WhitelistTerm
from .models import Finding
from .rules import ALERT_LEVEL_TO_SEVERITY
from .text_utils import compact_text, normalize_for_matching, shorten, tokenize_words


REVIEW_SCORE_THRESHOLD = 0.65
CORRECTION_SCORE_THRESHOLD = 0.85


@dataclass(frozen=True, slots=True)
class Article9Match:
    """Internal match candidate before it is turned into a Finding."""

    configured_term: str
    matched_text: str
    detection_type: str
    score: float


def _word_pattern(term: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", flags=re.IGNORECASE)


def _score(base_score: float, modifier: float) -> float:
    return round(max(0.0, min(1.0, base_score + modifier)), 2)


def _looks_like_same_root(configured: str, token: str) -> bool:
    configured_stem = _simple_french_stem(configured)
    token_stem = _simple_french_stem(token)
    if len(configured_stem) < 5 or len(token_stem) < 5:
        return False
    return configured_stem == token_stem


def _simple_french_stem(token: str) -> str:
    for suffix in ("iques", "ique", "euses", "euse", "ments", "ment", "es", "s", "e"):
        if len(token) > len(suffix) + 4 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _iter_ngrams(tokens: list[str], size: int) -> list[str]:
    return [" ".join(tokens[index : index + size]) for index in range(len(tokens) - size + 1)]


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
) -> Article9Match | None:
    normalized_term = normalize_for_matching(configured_term)
    if not _word_pattern(normalized_term).search(normalized_section):
        return None

    return Article9Match(
        configured_term=configured_term,
        matched_text=configured_term,
        detection_type="synonym" if is_synonym else "exact",
        score=_score(base_score, -0.05 if is_synonym else 0.0),
    )


def _find_root_match(
    tokens: list[str],
    configured_term: str,
    base_score: float,
) -> Article9Match | None:
    normalized_term = normalize_for_matching(configured_term)
    term_tokens = tokenize_words(normalized_term)
    if len(term_tokens) != 1:
        return None

    term_token = term_tokens[0]
    for token in tokens:
        if token == term_token:
            continue
        if _looks_like_same_root(term_token, token):
            return Article9Match(
                configured_term=configured_term,
                matched_text=token,
                detection_type="root",
                score=_score(base_score, -0.08),
            )

    return None


def _find_fuzzy_match(
    tokens: list[str],
    configured_term: str,
    base_score: float,
    threshold: float,
) -> Article9Match | None:
    normalized_term = normalize_for_matching(configured_term)
    term_tokens = tokenize_words(normalized_term)
    if not term_tokens:
        return None

    candidates = tokens if len(term_tokens) == 1 else _iter_ngrams(tokens, len(term_tokens))
    best_candidate = ""
    best_ratio = 0.0
    for candidate in candidates:
        if candidate == normalized_term:
            continue
        ratio = SequenceMatcher(None, normalized_term, candidate).ratio()
        if ratio > best_ratio:
            best_candidate = candidate
            best_ratio = ratio

    if best_ratio < threshold:
        return None

    return Article9Match(
        configured_term=configured_term,
        matched_text=best_candidate,
        detection_type="fuzzy",
        score=_score(base_score, -0.15),
    )


def _best_match_for_rule(section_text: str, rule: Article9Term) -> Article9Match | None:
    normalized_section = normalize_for_matching(section_text)
    tokens = tokenize_words(section_text)
    best_match: Article9Match | None = None

    for configured_term in rule.terms:
        candidates = [
            _find_exact_match(normalized_section, configured_term, False, rule.base_score),
            _find_root_match(tokens, configured_term, rule.base_score),
            _find_fuzzy_match(
                tokens,
                configured_term,
                rule.base_score,
                rule.fuzzy_threshold,
            ),
        ]
        best_match = _pick_best(best_match, candidates)

    for synonym in rule.synonyms:
        candidates = [
            _find_exact_match(normalized_section, synonym, True, rule.base_score),
            _find_fuzzy_match(tokens, synonym, rule.base_score, rule.fuzzy_threshold),
        ]
        best_match = _pick_best(best_match, candidates)

    return best_match


def _pick_best(
    current: Article9Match | None,
    candidates: list[Article9Match | None],
) -> Article9Match | None:
    valid_candidates = [candidate for candidate in candidates if candidate is not None]
    if current is not None:
        valid_candidates.append(current)
    if not valid_candidates:
        return None
    return max(valid_candidates, key=lambda candidate: candidate.score)


def _action_from_score(score: float) -> str:
    if score >= CORRECTION_SCORE_THRESHOLD:
        return "controle_humain_correction"
    if score >= REVIEW_SCORE_THRESHOLD:
        return "controle_humain"
    return "journalisation"


def analyze_article9_section(
    section_name: str,
    section_text: str,
    article9_terms: list[Article9Term],
    whitelist: list[WhitelistTerm] | None = None,
) -> list[Finding]:
    """Detect Article 9 sensitive data in a section."""

    findings: list[Finding] = []
    compact_section = compact_text(section_text)
    if not compact_section:
        return findings

    whitelist = whitelist or []
    for rule in article9_terms:
        match = _best_match_for_rule(compact_section, rule)
        if match is None:
            continue
        if _is_whitelisted(match.matched_text, compact_section, whitelist):
            continue

        action = _action_from_score(match.score)
        findings.append(
            Finding(
                code=f"article9_{rule.category}",
                severity=ALERT_LEVEL_TO_SEVERITY[rule.alert_level],
                section=section_name,
                title=f"Donnee sensible Article 9 detectee: {rule.label}",
                detail=(
                    f"Rule '{rule.rule_id}' detected '{match.matched_text}' "
                    f"as {match.detection_type}. Recommended action: {action}."
                ),
                evidence=shorten(compact_section),
                matched_term=match.matched_text,
                alert_level=rule.alert_level,
                category=rule.category,
                score=match.score,
                detection_type=match.detection_type,
                rule_id=rule.rule_id,
            )
        )

    return findings
