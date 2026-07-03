"""End-to-end analysis pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from .config import (
    GenericDetectionRule,
    WhitelistTerm,
    load_generic_detection_rules,
    load_whitelist_terms,
)
from .generic import analyze_generic_sections
from .gliner_detector import (
    DEFAULT_GLINER_LABEL_GROUPS,
    DEFAULT_GLINER_LABELS,
    DEFAULT_GLINER_MODEL,
    DEFAULT_GLINER_SOURCE_MODEL,
    DEFAULT_GLINER_THRESHOLD,
    DEFAULT_MODEL_CACHE_DIR,
    analyze_gliner_sections,
)
from .linguistic import DEFAULT_SPACY_MODEL, DEFAULT_SPACY_SYNONYMS_FILE, analyze_linguistic_sections
from .models import DocumentAnalysis, Finding
from .pdf import extract_text_from_pdf
from .regex_detector import analyze_regex_sections
from .text_utils import compact_text, normalize_for_matching, normalize_whitespace


def _build_sections(extracted_text: str) -> dict[str, str]:
    """Build the single document-level section used by compliance rules."""

    text = normalize_whitespace(extracted_text)
    return {"document": text}


def _normalize_enabled_branches(enabled_branches: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if enabled_branches is None:
        return ("generic",)
    normalized = tuple(branch.strip().lower() for branch in enabled_branches if branch.strip())
    unknown = set(normalized) - {"generic", "spacy", "gliner", "regex"}
    if unknown:
        raise ValueError(f"Unknown detection branch(es): {', '.join(sorted(unknown))}")
    return normalized


def _whitelist_match(
    finding: Finding,
    section_text: str,
    whitelist_terms: list[WhitelistTerm],
) -> WhitelistTerm | None:
    matched_text = finding.matched_term or ""
    if not matched_text:
        return None

    normalized_match = normalize_for_matching(matched_text)
    normalized_section = normalize_for_matching(section_text)
    if not normalized_match or not normalized_section:
        return None

    for item in whitelist_terms:
        normalized_expression = normalize_for_matching(item.expression)
        if not normalized_expression or normalized_expression not in normalized_section:
            continue
        if normalized_match in normalized_expression or normalized_expression in normalized_match:
            return item

    return None


def _apply_whitelist_filter(
    findings: list[Finding],
    sections: dict[str, str],
    whitelist_terms: list[WhitelistTerm],
) -> tuple[list[Finding], list[dict[str, object]]]:
    active_findings: list[Finding] = []
    ignored_findings: list[dict[str, object]] = []

    for finding in findings:
        section_text = sections.get(finding.section, "")
        whitelist_item = _whitelist_match(finding, section_text, whitelist_terms)
        if whitelist_item is None:
            active_findings.append(finding)
            continue

        ignored_findings.append(
            {
                "finding": finding.to_dict(),
                "whitelist_expression": whitelist_item.expression,
                "whitelist_reason": whitelist_item.reason,
                "ignore_reason": "whitelist",
            }
        )

    return active_findings, ignored_findings


def _count_by_engine(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        engine = finding.detection_engine or "unknown"
        counts[engine] = counts.get(engine, 0) + 1
    return counts


def _gliner_labels_metadata(
    gliner_labels: dict[str, list[str] | tuple[str, ...]] | tuple[str, ...] | list[str] | None,
) -> tuple[list[str], dict[str, list[str]] | None]:
    if gliner_labels is None:
        groups = {
            group_name: list(labels)
            for group_name, labels in DEFAULT_GLINER_LABEL_GROUPS.items()
        }
        return list(DEFAULT_GLINER_LABELS), groups
    if isinstance(gliner_labels, dict):
        groups = {
            group_name: [label for label in labels if label]
            for group_name, labels in gliner_labels.items()
        }
        labels = [label for group_labels in groups.values() for label in group_labels]
        return labels, groups
    return list(gliner_labels), None


def analyze_text(
    document_name: str,
    source_path: str,
    extracted_text: str,
    generic_rules: list[GenericDetectionRule] | None = None,
    whitelist_terms: list[WhitelistTerm] | None = None,
    enabled_branches: tuple[str, ...] | list[str] | None = None,
    spacy_model: str = DEFAULT_SPACY_MODEL,
    spacy_synonyms_path: str = DEFAULT_SPACY_SYNONYMS_FILE,
    gliner_model: str = DEFAULT_GLINER_MODEL,
    gliner_cache_dir: str | None = str(DEFAULT_MODEL_CACHE_DIR),
    gliner_source_model: str = DEFAULT_GLINER_SOURCE_MODEL,
    gliner_labels: dict[str, list[str] | tuple[str, ...]] | tuple[str, ...] | list[str] | None = None,
    gliner_threshold: float = DEFAULT_GLINER_THRESHOLD,
    gliner_local_files_only: bool = False,
) -> DocumentAnalysis:
    """Analyze already extracted text."""

    sections = _build_sections(extracted_text)
    if generic_rules is None:
        generic_rules = load_generic_detection_rules()
    if whitelist_terms is None:
        whitelist_terms = load_whitelist_terms()
    enabled_branches = _normalize_enabled_branches(enabled_branches)

    raw_findings: list[Finding] = []
    branch_errors: dict[str, str] = {}

    if "generic" in enabled_branches:
        raw_findings.extend(
            analyze_generic_sections(
                sections,
                generic_rules,
            )
        )

    if "spacy" in enabled_branches:
        try:
            raw_findings.extend(
                analyze_linguistic_sections(
                    sections,
                    generic_rules,
                    spacy_model=spacy_model,
                    spacy_synonyms_path=spacy_synonyms_path,
                )
            )
        except RuntimeError as exc:
            branch_errors["spacy"] = str(exc)

    if "gliner" in enabled_branches:
        try:
            raw_findings.extend(
                analyze_gliner_sections(
                    sections,
                    labels=gliner_labels,
                    threshold=gliner_threshold,
                    model_name=gliner_model,
                    cache_dir=gliner_cache_dir,
                    source_model=gliner_source_model,
                    local_files_only=gliner_local_files_only,
                )
            )
        except RuntimeError as exc:
            branch_errors["gliner"] = str(exc)

    if "regex" in enabled_branches:
        raw_findings.extend(analyze_regex_sections(sections))

    findings, ignored_findings = _apply_whitelist_filter(
        raw_findings,
        sections,
        whitelist_terms,
    )

    generic_findings = [finding for finding in findings if finding.detection_engine == "generic"]
    spacy_findings = [finding for finding in findings if finding.detection_engine == "spacy"]
    gliner_findings = [finding for finding in findings if finding.detection_engine == "gliner"]
    regex_findings = [finding for finding in findings if finding.detection_engine == "regex"]
    raw_counts_by_engine = _count_by_engine(raw_findings)
    ignored_counts_by_engine: dict[str, int] = {}
    for item in ignored_findings:
        ignored = item["finding"]
        if not isinstance(ignored, dict):
            continue
        engine = str(ignored.get("detection_engine") or "unknown")
        ignored_counts_by_engine[engine] = ignored_counts_by_engine.get(engine, 0) + 1
    resolved_gliner_labels, resolved_gliner_label_groups = _gliner_labels_metadata(gliner_labels)

    return DocumentAnalysis(
        document_name=document_name,
        source_path=source_path,
        extracted_text=compact_text(extracted_text),
        sections=sections,
        findings=findings,
        metadata={
            "finding_count": len(findings),
            "has_findings": bool(findings),
            "raw_finding_count": len(raw_findings),
            "whitelist_ignored_count": len(ignored_findings),
            "whitelist_ignored_findings": ignored_findings,
            "raw_finding_count_by_engine": raw_counts_by_engine,
            "whitelist_ignored_count_by_engine": ignored_counts_by_engine,
            "enabled_branches": list(enabled_branches),
            "spacy_model": spacy_model,
            "spacy_synonyms_path": spacy_synonyms_path,
            "gliner_model": gliner_model,
            "gliner_cache_dir": gliner_cache_dir,
            "gliner_source_model": gliner_source_model,
            "gliner_labels": resolved_gliner_labels,
            "gliner_label_groups": resolved_gliner_label_groups,
            "gliner_threshold": gliner_threshold,
            "gliner_local_files_only": gliner_local_files_only,
            "branch_errors": branch_errors,
            "generic_finding_count": len(generic_findings),
            "spacy_finding_count": len(spacy_findings),
            "gliner_finding_count": len(gliner_findings),
            "regex_finding_count": len(regex_findings),
            "generic_max_score": max(
                [finding.generic_score for finding in generic_findings if finding.generic_score is not None],
                default=None,
            ),
            "spacy_max_score": max(
                [finding.spacy_score for finding in spacy_findings if finding.spacy_score is not None],
                default=None,
            ),
            "gliner_max_score": max(
                [finding.gliner_score for finding in gliner_findings if finding.gliner_score is not None],
                default=None,
            ),
            "regex_max_score": max(
                [finding.regex_score for finding in regex_findings if finding.regex_score is not None],
                default=None,
            ),
            "central_rules_loaded": len(generic_rules),
            "generic_rules_loaded": len(generic_rules),
            "analysis_scope": "document",
            "whitelist_terms_loaded": len(whitelist_terms),
        },
    )


def analyze_file(
    pdf_path: str | Path,
    generic_rules: list[GenericDetectionRule] | None = None,
    whitelist_terms: list[WhitelistTerm] | None = None,
    generic_rules_path: str | Path | None = None,
    whitelist_path: str | Path | None = None,
    enabled_branches: tuple[str, ...] | list[str] | None = None,
    spacy_model: str = DEFAULT_SPACY_MODEL,
    spacy_synonyms_path: str = DEFAULT_SPACY_SYNONYMS_FILE,
    gliner_model: str = DEFAULT_GLINER_MODEL,
    gliner_cache_dir: str | None = str(DEFAULT_MODEL_CACHE_DIR),
    gliner_source_model: str = DEFAULT_GLINER_SOURCE_MODEL,
    gliner_labels: dict[str, list[str] | tuple[str, ...]] | tuple[str, ...] | list[str] | None = None,
    gliner_threshold: float = DEFAULT_GLINER_THRESHOLD,
    gliner_local_files_only: bool = False,
) -> DocumentAnalysis:
    """Analyze a single PDF file."""

    path = Path(pdf_path)
    extracted_text = extract_text_from_pdf(path)
    resolved_generic_rules = generic_rules
    if resolved_generic_rules is None:
        resolved_generic_rules = load_generic_detection_rules(generic_rules_path)
    resolved_whitelist_terms = whitelist_terms
    if resolved_whitelist_terms is None:
        resolved_whitelist_terms = load_whitelist_terms(whitelist_path)

    return analyze_text(
        path.name,
        str(path),
        extracted_text,
        generic_rules=resolved_generic_rules,
        whitelist_terms=resolved_whitelist_terms,
        enabled_branches=enabled_branches,
        spacy_model=spacy_model,
        spacy_synonyms_path=spacy_synonyms_path,
        gliner_model=gliner_model,
        gliner_cache_dir=gliner_cache_dir,
        gliner_source_model=gliner_source_model,
        gliner_labels=gliner_labels,
        gliner_threshold=gliner_threshold,
        gliner_local_files_only=gliner_local_files_only,
    )


def analyze_directory(
    input_dir: str | Path,
    output_path: str | Path | None = None,
    generic_rules_path: str | Path | None = None,
    whitelist_path: str | Path | None = None,
    enabled_branches: tuple[str, ...] | list[str] | None = None,
    spacy_model: str = DEFAULT_SPACY_MODEL,
    spacy_synonyms_path: str = DEFAULT_SPACY_SYNONYMS_FILE,
    gliner_model: str = DEFAULT_GLINER_MODEL,
    gliner_cache_dir: str | None = str(DEFAULT_MODEL_CACHE_DIR),
    gliner_source_model: str = DEFAULT_GLINER_SOURCE_MODEL,
    gliner_labels: dict[str, list[str] | tuple[str, ...]] | tuple[str, ...] | list[str] | None = None,
    gliner_threshold: float = DEFAULT_GLINER_THRESHOLD,
    gliner_local_files_only: bool = False,
) -> list[DocumentAnalysis]:
    """Analyze every PDF in a directory and optionally persist results."""

    directory = Path(input_dir)
    pdf_files = sorted(directory.glob("*.pdf"))
    generic_rules = load_generic_detection_rules(generic_rules_path)
    whitelist_terms = load_whitelist_terms(whitelist_path)
    results = [
        analyze_file(
            pdf_path,
            generic_rules=generic_rules,
            whitelist_terms=whitelist_terms,
            enabled_branches=enabled_branches,
            spacy_model=spacy_model,
            spacy_synonyms_path=spacy_synonyms_path,
            gliner_model=gliner_model,
            gliner_cache_dir=gliner_cache_dir,
            gliner_source_model=gliner_source_model,
            gliner_labels=gliner_labels,
            gliner_threshold=gliner_threshold,
            gliner_local_files_only=gliner_local_files_only,
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
