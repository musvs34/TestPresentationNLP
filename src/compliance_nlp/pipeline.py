"""End-to-end analysis pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from .config import (
    GenericDetectionRule,
    SectionDefinition,
    WhitelistTerm,
    load_generic_detection_rules,
    load_section_definitions,
    load_whitelist_terms,
)
from .generic import analyze_generic_sections
from .linguistic import DEFAULT_SPACY_MODEL, analyze_linguistic_sections
from .models import DocumentAnalysis, Finding
from .pdf import extract_text_from_pdf
from .text_utils import compact_text, extract_section, normalize_whitespace


def _build_sections(
    extracted_text: str,
    section_definitions: list[SectionDefinition],
) -> dict[str, str]:
    """Extract configured sections used by compliance rules."""

    text = normalize_whitespace(extracted_text)
    sections: dict[str, str] = {}
    for section in section_definitions:
        if section.section_id == "document" or not section.start_marker:
            sections[section.section_id] = text
            continue
        sections[section.section_id] = extract_section(
            text,
            section.start_marker,
            section.end_marker,
        )
    return sections


def _normalize_enabled_branches(enabled_branches: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if enabled_branches is None:
        return ("generic",)
    normalized = tuple(branch.strip().lower() for branch in enabled_branches if branch.strip())
    unknown = set(normalized) - {"generic", "spacy"}
    if unknown:
        raise ValueError(f"Unknown detection branch(es): {', '.join(sorted(unknown))}")
    return normalized


def analyze_text(
    document_name: str,
    source_path: str,
    extracted_text: str,
    generic_rules: list[GenericDetectionRule] | None = None,
    section_definitions: list[SectionDefinition] | None = None,
    whitelist_terms: list[WhitelistTerm] | None = None,
    enabled_branches: tuple[str, ...] | list[str] | None = None,
    spacy_model: str = DEFAULT_SPACY_MODEL,
) -> DocumentAnalysis:
    """Analyze already extracted text."""

    section_definitions = section_definitions or load_section_definitions()
    sections = _build_sections(extracted_text, section_definitions)
    if generic_rules is None:
        generic_rules = load_generic_detection_rules()
    if whitelist_terms is None:
        whitelist_terms = load_whitelist_terms()
    enabled_branches = _normalize_enabled_branches(enabled_branches)

    findings: list[Finding] = []
    branch_errors: dict[str, str] = {}

    if "generic" in enabled_branches:
        findings.extend(
            analyze_generic_sections(
                sections,
                generic_rules,
                whitelist_terms=whitelist_terms,
            )
        )

    if "spacy" in enabled_branches:
        try:
            findings.extend(
                analyze_linguistic_sections(
                    sections,
                    generic_rules,
                    whitelist_terms=whitelist_terms,
                    spacy_model=spacy_model,
                )
            )
        except RuntimeError as exc:
            branch_errors["spacy"] = str(exc)

    generic_findings = [finding for finding in findings if finding.detection_engine == "generic"]
    spacy_findings = [finding for finding in findings if finding.detection_engine == "spacy"]

    return DocumentAnalysis(
        document_name=document_name,
        source_path=source_path,
        extracted_text=compact_text(extracted_text),
        sections=sections,
        findings=findings,
        metadata={
            "finding_count": len(findings),
            "has_findings": bool(findings),
            "enabled_branches": list(enabled_branches),
            "spacy_model": spacy_model,
            "branch_errors": branch_errors,
            "generic_finding_count": len(generic_findings),
            "spacy_finding_count": len(spacy_findings),
            "generic_max_score": max(
                [finding.generic_score for finding in generic_findings if finding.generic_score is not None],
                default=None,
            ),
            "spacy_max_score": max(
                [finding.spacy_score for finding in spacy_findings if finding.spacy_score is not None],
                default=None,
            ),
            "central_rules_loaded": len(generic_rules),
            "generic_rules_loaded": len(generic_rules),
            "sections_loaded": len(section_definitions),
            "whitelist_terms_loaded": len(whitelist_terms),
        },
    )


def analyze_file(
    pdf_path: str | Path,
    generic_rules: list[GenericDetectionRule] | None = None,
    section_definitions: list[SectionDefinition] | None = None,
    whitelist_terms: list[WhitelistTerm] | None = None,
    generic_rules_path: str | Path | None = None,
    sections_path: str | Path | None = None,
    whitelist_path: str | Path | None = None,
    enabled_branches: tuple[str, ...] | list[str] | None = None,
    spacy_model: str = DEFAULT_SPACY_MODEL,
) -> DocumentAnalysis:
    """Analyze a single PDF file."""

    path = Path(pdf_path)
    extracted_text = extract_text_from_pdf(path)
    resolved_generic_rules = generic_rules
    if resolved_generic_rules is None:
        resolved_generic_rules = load_generic_detection_rules(generic_rules_path)
    resolved_section_definitions = section_definitions
    if resolved_section_definitions is None:
        resolved_section_definitions = load_section_definitions(sections_path)
    resolved_whitelist_terms = whitelist_terms
    if resolved_whitelist_terms is None:
        resolved_whitelist_terms = load_whitelist_terms(whitelist_path)

    return analyze_text(
        path.name,
        str(path),
        extracted_text,
        generic_rules=resolved_generic_rules,
        section_definitions=resolved_section_definitions,
        whitelist_terms=resolved_whitelist_terms,
        enabled_branches=enabled_branches,
        spacy_model=spacy_model,
    )


def analyze_directory(
    input_dir: str | Path,
    output_path: str | Path | None = None,
    generic_rules_path: str | Path | None = None,
    sections_path: str | Path | None = None,
    whitelist_path: str | Path | None = None,
    enabled_branches: tuple[str, ...] | list[str] | None = None,
    spacy_model: str = DEFAULT_SPACY_MODEL,
) -> list[DocumentAnalysis]:
    """Analyze every PDF in a directory and optionally persist results."""

    directory = Path(input_dir)
    pdf_files = sorted(directory.glob("*.pdf"))
    generic_rules = load_generic_detection_rules(generic_rules_path)
    section_definitions = load_section_definitions(sections_path)
    whitelist_terms = load_whitelist_terms(whitelist_path)
    results = [
        analyze_file(
            pdf_path,
            generic_rules=generic_rules,
            section_definitions=section_definitions,
            whitelist_terms=whitelist_terms,
            enabled_branches=enabled_branches,
            spacy_model=spacy_model,
        )
        for pdf_path in pdf_files
    ]

    if output_path is not None:
        save_results(results, output_path)

    return results


def save_results(results: list[DocumentAnalysis], output_path: str | Path) -> Path:
    """Serialize analysis results to JSON."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [result.to_dict() for result in results]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return path


def load_results(input_path: str | Path) -> list[DocumentAnalysis]:
    """Load previously saved results from JSON."""

    path = Path(input_path)
    raw_payload = json.loads(path.read_text(encoding="utf-8"))

    analyses: list[DocumentAnalysis] = []
    for item in raw_payload:
        findings = [Finding(**finding) for finding in item.get("findings", [])]
        analyses.append(
            DocumentAnalysis(
                document_name=item["document_name"],
                source_path=item["source_path"],
                extracted_text=item.get("extracted_text", ""),
                sections=item.get("sections", {}),
                findings=findings,
                metadata=item.get("metadata", {}),
            )
        )

    return analyses
