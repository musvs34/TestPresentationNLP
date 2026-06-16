"""Rule-based detectors for the POC."""

from __future__ import annotations

import re

from .config import ForbiddenTerm
from .models import Finding
from .text_utils import compact_text, shorten


ALERT_LEVEL_TO_SEVERITY = {
    "interdit": "high",
    "alerte": "medium",
    "ambigue": "low",
}


def analyze_beneficiary_section(section_text: str) -> list[Finding]:
    """Detect ambiguous beneficiary clauses."""

    findings: list[Finding] = []
    lowered = section_text.lower()

    ambiguous_markers = [
        "la personne qui sera la plus presente",
        "si notre situation est toujours stable",
        "mes proches",
        "toute autre personne dont mon fils connaitra le nom",
        "au moment venu",
    ]

    if any(marker in lowered for marker in ambiguous_markers):
        findings.append(
            Finding(
                code="beneficiary_clause_imprecise",
                severity="high",
                section="beneficiaires",
                title="Clause beneficiaire imprecise",
                detail=(
                    "The beneficiary designation uses subjective or unstable wording "
                    "that is hard to interpret or enforce."
                ),
                evidence=shorten(section_text),
            )
        )

    return findings


def analyze_forbidden_terms(
    section_name: str,
    section_text: str,
    forbidden_terms: list[ForbiddenTerm],
) -> list[Finding]:
    """Detect configured terms in a specific section."""

    findings: list[Finding] = []
    haystack = compact_text(section_text).lower()
    if not haystack:
        return findings

    for forbidden_term in forbidden_terms:
        pattern = re.compile(
            rf"(?<!\w){re.escape(forbidden_term.term)}(?!\w)",
            flags=re.IGNORECASE,
        )
        if not pattern.search(haystack):
            continue

        findings.append(
            Finding(
                code=f"forbidden_term_{forbidden_term.alert_level}",
                severity=ALERT_LEVEL_TO_SEVERITY[forbidden_term.alert_level],
                section=section_name,
                title=f"Terme surveille detecte dans la section {section_name}",
                detail=(
                    f"The configured term '{forbidden_term.term}' was detected in the "
                    f"'{section_name}' section with alert level "
                    f"'{forbidden_term.alert_level}'."
                ),
                evidence=shorten(section_text),
                matched_term=forbidden_term.term,
                alert_level=forbidden_term.alert_level,
            )
        )

    return findings


def analyze_advice_section(section_text: str) -> list[Finding]:
    """Detect risky advice formulations."""

    findings: list[Finding] = []
    lowered = section_text.lower()

    def add_finding(
        code: str,
        severity: str,
        title: str,
        detail: str,
    ) -> None:
        findings.append(
            Finding(
                code=code,
                severity=severity,
                section="conseil",
                title=title,
                detail=detail,
                evidence=shorten(section_text),
            )
        )

    if any(
        marker in lowered
        for marker in [
            "foncer sans trop reflechir",
            "ce contrat est top",
            "pas besoin d'entrer dans trop de details",
        ]
    ):
        add_finding(
            code="advice_unprofessional_wording",
            severity="high",
            title="Conseil formule de maniere non professionnelle",
            detail=(
                "The advice section contains overly informal language that is not "
                "compatible with professional advisory documentation."
            ),
        )

    if any(
        marker in lowered
        for marker in [
            "rapporte forcement sur la duree",
            "les risques ne sont pas un vrai sujet",
            "ca finit toujours par remonter",
        ]
    ):
        add_finding(
            code="advice_risk_minimization",
            severity="high",
            title="Risques minimises ou performance suggeree",
            detail=(
                "The advice text appears to minimize market risk or imply guaranteed "
                "performance."
            ),
        )

    if any(
        marker in lowered
        for marker in [
            "represente une part tres importante du revenu disponible",
            "depasse ses capacites actuelles",
            "reduire fortement ses autres depenses",
        ]
    ):
        add_finding(
            code="advice_above_financial_capacity",
            severity="high",
            title="Formule proposee au-dessus des capacites de l'adherent",
            detail=(
                "The advice acknowledges that the recommended contribution level is "
                "above the member's realistic financial capacity."
            ),
        )

    if any(
        marker in lowered
        for marker in [
            "ne comprand pas bien",
            "ne saisi pas bien",
            "formule par defaut",
            "formule standart du cabinet",
            "pour aller plus vite",
        ]
    ):
        add_finding(
            code="advice_default_formula_due_to_client_confusion",
            severity="high",
            title="Formule par defaut retenue faute d'accompagnement adapte",
            detail=(
                "The advice suggests the product choice was defaulted because the "
                "member did not understand the explanations."
            ),
        )

    if any(
        marker in lowered
        for marker in [
            "comprand",
            "diferences",
            "plusieur",
            "disponnibilite",
            "detaille",
            "preferer",
            "standart",
        ]
    ):
        add_finding(
            code="advice_spelling_quality_issue",
            severity="medium",
            title="Qualite redactionnelle faible dans la zone conseil",
            detail=(
                "The advice section contains multiple spelling issues, which may be a "
                "useful signal for document quality controls."
            ),
        )

    return findings
