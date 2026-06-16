"""End-to-end analysis pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from .config import (
    Article9Term,
    ForbiddenTerm,
    GenericDetectionRule,
    SectionDefinition,
    WhitelistTerm,
    article9_terms_to_generic_rules,
    load_article9_terms,
    load_forbidden_terms,
    load_generic_detection_rules,
    load_section_definitions,
    load_whitelist_terms,
)
from .generic import analyze_generic_sections
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


def analyze_text(
    document_name: str,
    source_path: str,
    extracted_text: str,
    forbidden_terms: list[ForbiddenTerm] | None = None,
    generic_rules: list[GenericDetectionRule] | None = None,
    section_definitions: list[SectionDefinition] | None = None,
    article9_terms: list[Article9Term] | None = None,
    whitelist_terms: list[WhitelistTerm] | None = None,
) -> DocumentAnalysis:
    """Analyze already extracted text."""

    section_definitions = section_definitions or load_section_definitions()
    sections = _build_sections(extracted_text, section_definitions)
    forbidden_terms = forbidden_terms or []
    if generic_rules is None:
        generic_rules = load_generic_detection_rules()
    article9_terms = article9_terms or []
    if article9_terms:
        generic_rules = [*generic_rules, *article9_terms_to_generic_rules(article9_terms)]
    if whitelist_terms is None:
        whitelist_terms = load_whitelist_terms()

    findings: list[Finding] = []

    findings.extend(
        analyze_generic_sections(
            sections,
            generic_rules,
            whitelist_terms=whitelist_terms,
        )
    )

    return DocumentAnalysis(
        document_name=document_name,
        source_path=source_path,
        extracted_text=compact_text(extracted_text),
        sections=sections,
        findings=findings,
        metadata={
            "finding_count": len(findings),
            "has_findings": bool(findings),
            "forbidden_terms_loaded": len(forbidden_terms),
            "central_rules_loaded": len(generic_rules),
            "generic_rules_loaded": len(generic_rules),
            "sections_loaded": len(section_definitions),
            "legacy_article9_terms_loaded": len(article9_terms),
            "whitelist_terms_loaded": len(whitelist_terms),
        },
    )


def analyze_file(
    pdf_path: str | Path,
    forbidden_terms: list[ForbiddenTerm] | None = None,
    generic_rules: list[GenericDetectionRule] | None = None,
    section_definitions: list[SectionDefinition] | None = None,
    article9_terms: list[Article9Term] | None = None,
    whitelist_terms: list[WhitelistTerm] | None = None,
    forbidden_words_path: str | Path | None = None,
    generic_rules_path: str | Path | None = None,
    sections_path: str | Path | None = None,
    article9_terms_path: str | Path | None = None,
    whitelist_path: str | Path | None = None,
) -> DocumentAnalysis:
    """Analyze a single PDF file."""

    path = Path(pdf_path)
    extracted_text = extract_text_from_pdf(path)
    resolved_terms = forbidden_terms
    if resolved_terms is None:
        resolved_terms = load_forbidden_terms(forbidden_words_path)
    resolved_generic_rules = generic_rules
    if resolved_generic_rules is None:
        resolved_generic_rules = load_generic_detection_rules(generic_rules_path)
    resolved_section_definitions = section_definitions
    if resolved_section_definitions is None:
        resolved_section_definitions = load_section_definitions(sections_path)
    resolved_article9_terms = article9_terms
    if resolved_article9_terms is None and article9_terms_path is not None:
        resolved_article9_terms = load_article9_terms(article9_terms_path)
    resolved_whitelist_terms = whitelist_terms
    if resolved_whitelist_terms is None:
        resolved_whitelist_terms = load_whitelist_terms(whitelist_path)

    return analyze_text(
        path.name,
        str(path),
        extracted_text,
        forbidden_terms=resolved_terms,
        generic_rules=resolved_generic_rules,
        section_definitions=resolved_section_definitions,
        article9_terms=resolved_article9_terms,
        whitelist_terms=resolved_whitelist_terms,
    )


def analyze_directory(
    input_dir: str | Path,
    output_path: str | Path | None = None,
    forbidden_words_path: str | Path | None = None,
    generic_rules_path: str | Path | None = None,
    sections_path: str | Path | None = None,
    article9_terms_path: str | Path | None = None,
    whitelist_path: str | Path | None = None,
) -> list[DocumentAnalysis]:
    """Analyze every PDF in a directory and optionally persist results."""

    directory = Path(input_dir)
    pdf_files = sorted(directory.glob("*.pdf"))
    forbidden_terms = load_forbidden_terms(forbidden_words_path)
    generic_rules = load_generic_detection_rules(generic_rules_path)
    section_definitions = load_section_definitions(sections_path)
    article9_terms = load_article9_terms(article9_terms_path) if article9_terms_path else []
    whitelist_terms = load_whitelist_terms(whitelist_path)
    results = [
        analyze_file(
            pdf_path,
            forbidden_terms=forbidden_terms,
            generic_rules=generic_rules,
            section_definitions=section_definitions,
            article9_terms=article9_terms,
            whitelist_terms=whitelist_terms,
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
