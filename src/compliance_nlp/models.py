"""Domain models for document analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Finding:
    """A compliance issue detected in a document."""

    code: str
    severity: str
    section: str
    title: str
    detail: str
    evidence: str
    matched_term: str | None = None
    alert_level: str | None = None
    category: str | None = None
    score: float | None = None
    branch_score: float | None = None
    generic_score: float | None = None
    spacy_score: float | None = None
    detection_type: str | None = None
    detection_engine: str | None = None
    rule_id: str | None = None
    rule_scope: str | None = None
    regulatory_family: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DocumentAnalysis:
    """A fully analyzed document."""

    document_name: str
    source_path: str
    extracted_text: str
    sections: dict[str, str] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["findings"] = [finding.to_dict() for finding in self.findings]
        return payload
