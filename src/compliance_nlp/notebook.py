"""Notebook-oriented helpers."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .models import DocumentAnalysis


def findings_to_records(results: list[DocumentAnalysis]) -> list[dict[str, Any]]:
    """Flatten findings so notebooks can filter and aggregate them easily."""

    records: list[dict[str, Any]] = []
    for result in results:
        if not result.findings:
            records.append(
                {
                    "document_name": result.document_name,
                    "source_path": result.source_path,
                    "code": None,
                    "severity": None,
                    "alert_level": None,
                    "section": None,
                    "title": None,
                    "detail": None,
                    "evidence": None,
                    "matched_term": None,
                    "category": None,
                    "score": None,
                    "branch_score": None,
                    "generic_score": None,
                    "spacy_score": None,
                    "gliner_score": None,
                    "regex_score": None,
                    "detection_type": None,
                    "detection_engine": None,
                    "rule_id": None,
                    "rule_scope": None,
                    "regulatory_family": None,
                    "finding_count": 0,
                }
            )
            continue

        for finding in result.findings:
            records.append(
                {
                    "document_name": result.document_name,
                    "source_path": result.source_path,
                    "code": finding.code,
                    "severity": finding.severity,
                    "alert_level": finding.alert_level,
                    "section": finding.section,
                    "title": finding.title,
                    "detail": finding.detail,
                    "evidence": finding.evidence,
                    "matched_term": finding.matched_term,
                    "category": finding.category,
                    "score": finding.score,
                    "branch_score": finding.branch_score,
                    "generic_score": finding.generic_score,
                    "spacy_score": finding.spacy_score,
                    "gliner_score": finding.gliner_score,
                    "regex_score": finding.regex_score,
                    "detection_type": finding.detection_type,
                    "detection_engine": finding.detection_engine,
                    "rule_id": finding.rule_id,
                    "rule_scope": finding.rule_scope,
                    "regulatory_family": finding.regulatory_family,
                    "finding_count": len(result.findings),
                }
            )

    return records


def results_to_dataframe(results: list[DocumentAnalysis]):  # type: ignore[no-untyped-def]
    """Convert flattened records to a pandas DataFrame when available."""

    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "pandas is required for DataFrame output. Install it or use findings_to_records()."
        ) from exc

    return pd.DataFrame(findings_to_records(results))


def summarize_results(results: list[DocumentAnalysis]) -> dict[str, Any]:
    """Return a compact summary for notebook dashboards."""

    all_findings = findings_to_records(results)
    codes = [record["code"] for record in all_findings if record["code"]]

    return {
        "document_count": len(results),
        "documents_with_findings": sum(1 for result in results if result.findings),
        "total_findings": sum(len(result.findings) for result in results),
        "finding_codes": dict(Counter(codes)),
    }
