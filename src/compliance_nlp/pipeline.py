"""End-to-end analysis pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from .article9 import analyze_article9_section
from .config import (
    Article9Term,
    ForbiddenTerm,
    WhitelistTerm,
    load_article9_terms,
    load_forbidden_terms,
    load_whitelist_terms,
)
from .models import DocumentAnalysis, Finding
from .pdf import extract_text_from_pdf
from .rules import analyze_advice_section, analyze_beneficiary_section, analyze_forbidden_terms
from .text_utils import compact_text, extract_section, normalize_whitespace


def _build_sections(extracted_text: str) -> dict[str, str]:
    """Extract the sections most useful for compliance rules."""

    text = normalize_whitespace(extracted_text)
    return {
        "beneficiaires": extract_section(text, "7. Beneficiaires", "8. Declarations"),
        "conseil": extract_section(text, "9. Conseil et Recommandation", "10. Signatures"),
    }


def analyze_text(
    document_name: str,
    source_path: str,
    extracted_text: str,
    forbidden_terms: list[ForbiddenTerm] | None = None,
    article9_terms: list[Article9Term] | None = None,
    whitelist_terms: list[WhitelistTerm] | None = None,
) -> DocumentAnalysis:
    """Analyze already extracted text."""

    sections = _build_sections(extracted_text)
    forbidden_terms = forbidden_terms or []
    article9_terms = article9_terms or []
    whitelist_terms = whitelist_terms or []

    findings: list[Finding] = []
    beneficiary_section = sections.get("beneficiaires", "")
    advice_section = sections.get("conseil", "")

    findings.extend(analyze_beneficiary_section(beneficiary_section))
    findings.extend(analyze_advice_section(advice_section))
    findings.extend(analyze_forbidden_terms("beneficiaires", beneficiary_section, forbidden_terms))
    findings.extend(analyze_forbidden_terms("conseil", advice_section, forbidden_terms))
    findings.extend(
        analyze_article9_section(
            "document",
            extracted_text,
            article9_terms=article9_terms,
            whitelist=whitelist_terms,
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
            "article9_terms_loaded": len(article9_terms),
            "whitelist_terms_loaded": len(whitelist_terms),
        },
    )


def analyze_file(
    pdf_path: str | Path,
    forbidden_terms: list[ForbiddenTerm] | None = None,
    article9_terms: list[Article9Term] | None = None,
    whitelist_terms: list[WhitelistTerm] | None = None,
    forbidden_words_path: str | Path | None = None,
    article9_terms_path: str | Path | None = None,
    whitelist_path: str | Path | None = None,
) -> DocumentAnalysis:
    """Analyze a single PDF file."""

    path = Path(pdf_path)
    extracted_text = extract_text_from_pdf(path)
    resolved_terms = forbidden_terms
    if resolved_terms is None:
        resolved_terms = load_forbidden_terms(forbidden_words_path)
    resolved_article9_terms = article9_terms
    if resolved_article9_terms is None:
        resolved_article9_terms = load_article9_terms(article9_terms_path)
    resolved_whitelist_terms = whitelist_terms
    if resolved_whitelist_terms is None:
        resolved_whitelist_terms = load_whitelist_terms(whitelist_path)

    return analyze_text(
        path.name,
        str(path),
        extracted_text,
        forbidden_terms=resolved_terms,
        article9_terms=resolved_article9_terms,
        whitelist_terms=resolved_whitelist_terms,
    )


def analyze_directory(
    input_dir: str | Path,
    output_path: str | Path | None = None,
    forbidden_words_path: str | Path | None = None,
    article9_terms_path: str | Path | None = None,
    whitelist_path: str | Path | None = None,
) -> list[DocumentAnalysis]:
    """Analyze every PDF in a directory and optionally persist results."""

    directory = Path(input_dir)
    pdf_files = sorted(directory.glob("*.pdf"))
    forbidden_terms = load_forbidden_terms(forbidden_words_path)
    article9_terms = load_article9_terms(article9_terms_path)
    whitelist_terms = load_whitelist_terms(whitelist_path)
    results = [
        analyze_file(
            pdf_path,
            forbidden_terms=forbidden_terms,
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
