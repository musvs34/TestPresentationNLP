"""Regex-based structured personal data detection branch."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Pattern

from .models import Finding
from .text_utils import compact_text, shorten


@dataclass(frozen=True, slots=True)
class RegexRule:
    """A deterministic regex rule for structured identifiers."""

    entity_type: str
    title: str
    pattern: Pattern[str]
    score: float


REGEX_RULES = (
    RegexRule(
        entity_type="EMAIL_ADDRESS",
        title="Adresse email",
        pattern=re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
        score=0.95,
    ),
    RegexRule(
        entity_type="PHONE_NUMBER_FR",
        title="Numero de telephone francais",
        pattern=re.compile(r"(?<!\d)(?:\+33[\s.-]?|0)[1-9](?:[\s.-]?\d{2}){4}(?!\d)"),
        score=0.90,
    ),
    RegexRule(
        entity_type="IBAN_FR",
        title="IBAN francais",
        pattern=re.compile(r"(?i)\bFR\d{2}(?:[\s-]?[A-Z0-9]{4}){5}[\s-]?[A-Z0-9]{3}\b"),
        score=0.95,
    ),
    RegexRule(
        entity_type="FR_NIR",
        title="NIR francais",
        pattern=re.compile(
            r"(?i)\b[12]\s?\d{2}\s?(?:0[1-9]|1[0-2]|20)\s?"
            r"(?:\d{2}|2A|2B|97[1-6]|98[4678])\s?\d{3}\s?\d{3}\s?\d{2}\b"
        ),
        score=0.95,
    ),
)


def analyze_regex_section(
    section_name: str,
    section_text: str,
    rules: tuple[RegexRule, ...] = REGEX_RULES,
) -> list[Finding]:
    """Apply regex rules to one section."""

    compact_section = compact_text(section_text)
    if not compact_section:
        return []

    findings: list[Finding] = []
    for rule in rules:
        for match in rule.pattern.finditer(section_text):
            matched_text = match.group(0)
            findings.append(
                Finding(
                    code=f"regex_{rule.entity_type.lower()}",
                    severity="medium",
                    section=section_name,
                    title=rule.title,
                    detail=f"Regex detected '{matched_text}' as '{rule.entity_type}'.",
                    evidence=shorten(compact_section),
                    matched_term=matched_text,
                    alert_level="alerte",
                    category=rule.entity_type.lower(),
                    score=rule.score,
                    branch_score=rule.score,
                    regex_score=rule.score,
                    detection_type="regex",
                    detection_engine="regex",
                    rule_id=rule.entity_type,
                    rule_scope="regex",
                    regulatory_family="donnees_personnelles_structurees",
                )
            )

    return sorted(findings, key=lambda finding: (finding.section, finding.matched_term or "", finding.rule_id or ""))


def analyze_regex_sections(
    sections: dict[str, str],
    rules: tuple[RegexRule, ...] = REGEX_RULES,
) -> list[Finding]:
    """Apply regex rules to available sections without duplicating document-level text."""

    if "document" in sections:
        return analyze_regex_section("document", sections["document"], rules=rules)

    findings: list[Finding] = []
    for section_name, section_text in sections.items():
        findings.extend(analyze_regex_section(section_name, section_text, rules=rules))
    return findings
