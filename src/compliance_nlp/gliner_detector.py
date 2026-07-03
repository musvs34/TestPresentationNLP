"""GLiNER-based configurable named-entity detection branch."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from .models import Finding
from .text_utils import compact_text, normalize_for_matching, shorten


DEFAULT_MODEL_CACHE_DIR = Path(os.environ.get("COMPLIANCE_NLP_MODEL_CACHE", r"D:\Workspaces\ModelCache"))
DEFAULT_MODEL_STORE_DIR = Path(os.environ.get("COMPLIANCE_NLP_MODEL_STORE", r"D:\Workspaces\modelStore"))
DEFAULT_GLINER_SOURCE_MODEL = "urchade/gliner_multi-v2.1"
DEFAULT_GLINER_MODEL = str(DEFAULT_MODEL_STORE_DIR / "gliner_multi-v2.1")
DEFAULT_GLINER_THRESHOLD = 0.50
DEFAULT_GLINER_LABEL_GROUPS = {
    "sante": (
        "donnee de sante",
        "maladie",
        "pathologie",
        "autisme",
        "handicap",
        "trouble du neurodeveloppement",
        "etat de sante",
        "condition medicale",
        "probleme de sante",
    ),
    "politique": (
        "ideologie politique",
        "position politique",
    ),
    "religion": (
        "conviction religieuse",
        "religion",
        "appartenance religieuse",
    ),
    "syndical": (
        "appartenance syndicale",
        "engagement syndical",
    ),
    "orientation_sexuelle": (
        "orientation sexuelle",
    ),
    "origine": (
        "origine ethnique",
        "origine raciale",
    ),
    "biometrie_genetique": (
        "donnee genetique",
        "donnee biometrique",
    ),
    "conformite_conseil": (
        "clause beneficiaire imprecise",
        "conseil non professionnel",
        "promesse de performance",
    ),
}
DEFAULT_GLINER_LABELS = tuple(
    label for labels in DEFAULT_GLINER_LABEL_GROUPS.values() for label in labels
)


def _is_local_model_path(model_name: str) -> bool:
    path = Path(model_name)
    return path.is_absolute() or os.sep in model_name or (os.altsep is not None and os.altsep in model_name)


@lru_cache(maxsize=4)
def load_gliner_model(  # type: ignore[no-untyped-def]
    model_name: str = DEFAULT_GLINER_MODEL,
    cache_dir: str | None = str(DEFAULT_MODEL_CACHE_DIR),
    source_model: str = DEFAULT_GLINER_SOURCE_MODEL,
    local_files_only: bool = False,
):
    """Load and cache the configured GLiNER model."""

    try:
        from gliner import GLiNER
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "The GLiNER branch requires the 'gliner' package. Install optional NLP "
            "dependencies before enabling it."
        ) from exc

    try:
        if _is_local_model_path(model_name):
            local_path = Path(model_name)
            if local_path.exists():
                return GLiNER.from_pretrained(
                    str(local_path),
                    cache_dir=cache_dir,
                    local_files_only=True,
                )
            if local_files_only:
                raise RuntimeError(f"Local GLiNER model path does not exist: {local_path}")

            model = GLiNER.from_pretrained(
                source_model,
                cache_dir=cache_dir,
                local_files_only=False,
            )
            local_path.parent.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(str(local_path))
            return model

        return GLiNER.from_pretrained(
            model_name,
            cache_dir=cache_dir,
            local_files_only=local_files_only,
        )
    except Exception as exc:  # pragma: no cover - model download/local cache dependent
        raise RuntimeError(
            f"The GLiNER branch could not load model '{model_name}'. "
            "Install/cache the model before enabling the branch."
        ) from exc


def _label_to_code(label: str) -> str:
    normalized = normalize_for_matching(label)
    safe = "".join(character if character.isalnum() else "_" for character in normalized)
    return "gliner_" + "_".join(part for part in safe.split("_") if part)


def _normalize_labels(labels: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    labels = DEFAULT_GLINER_LABELS if labels is None else labels
    return tuple(label.strip() for label in labels if label and label.strip())


def _normalize_label_groups(
    labels: dict[str, list[str] | tuple[str, ...]] | list[str] | tuple[str, ...] | None,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if labels is None:
        source_groups = DEFAULT_GLINER_LABEL_GROUPS
    elif isinstance(labels, dict):
        source_groups = labels
    else:
        return (("default", _normalize_labels(labels)),)

    groups: list[tuple[str, tuple[str, ...]]] = []
    for group_name, group_labels in source_groups.items():
        normalized = _normalize_labels(tuple(group_labels))
        if normalized:
            groups.append((group_name, normalized))
    return tuple(groups)


def _finding_from_entity(
    entity: dict[str, object],
    section_name: str,
    compact_section: str,
    label_group: str,
) -> Finding | None:
    label = str(entity.get("label") or "").strip()
    matched_text = str(entity.get("text") or "").strip()
    score = entity.get("score")
    if not label or not matched_text:
        return None

    numeric_score = round(float(score), 2) if score is not None else None
    code = _label_to_code(label)
    return Finding(
        code=code,
        severity="medium",
        section=section_name,
        title=label,
        detail=f"GLiNER group '{label_group}' detected '{matched_text}' as '{label}'.",
        evidence=shorten(compact_section),
        matched_term=matched_text,
        alert_level="alerte",
        category=normalize_for_matching(label).replace(" ", "_"),
        score=numeric_score,
        branch_score=numeric_score,
        gliner_score=numeric_score,
        detection_type="entity",
        detection_engine="gliner",
        rule_id=code,
        rule_scope="gliner",
        regulatory_family="gliner",
    )


def _deduplicate_findings(findings: list[Finding]) -> list[Finding]:
    best_by_key: dict[tuple[str, str, str, str], Finding] = {}
    for finding in findings:
        key = (
            finding.section,
            finding.matched_term or "",
            finding.rule_id or "",
            finding.detection_engine or "",
        )
        current = best_by_key.get(key)
        if current is None or (finding.score or 0.0) > (current.score or 0.0):
            best_by_key[key] = finding
    return sorted(
        best_by_key.values(),
        key=lambda finding: (
            finding.section,
            finding.matched_term or "",
            finding.rule_id or "",
            -(finding.score or 0.0),
        ),
    )


def analyze_gliner_section(
    section_name: str,
    section_text: str,
    labels: dict[str, list[str] | tuple[str, ...]] | list[str] | tuple[str, ...] | None = None,
    threshold: float = DEFAULT_GLINER_THRESHOLD,
    model_name: str = DEFAULT_GLINER_MODEL,
    cache_dir: str | None = str(DEFAULT_MODEL_CACHE_DIR),
    source_model: str = DEFAULT_GLINER_SOURCE_MODEL,
    local_files_only: bool = False,
    model=None,  # type: ignore[no-untyped-def]
) -> list[Finding]:
    """Apply GLiNER zero-shot entity recognition to one section."""

    compact_section = compact_text(section_text)
    if not compact_section:
        return []

    label_groups = _normalize_label_groups(labels)
    if not label_groups:
        return []

    model = model or load_gliner_model(model_name, cache_dir, source_model, local_files_only)

    findings: list[Finding] = []
    for label_group, resolved_labels in label_groups:
        entities = model.predict_entities(
            compact_section,
            list(resolved_labels),
            threshold=threshold,
        )
        for entity in entities:
            finding = _finding_from_entity(entity, section_name, compact_section, label_group)
            if finding is not None:
                findings.append(finding)

    return _deduplicate_findings(findings)


def analyze_gliner_sections(
    sections: dict[str, str],
    labels: dict[str, list[str] | tuple[str, ...]] | list[str] | tuple[str, ...] | None = None,
    threshold: float = DEFAULT_GLINER_THRESHOLD,
    model_name: str = DEFAULT_GLINER_MODEL,
    cache_dir: str | None = str(DEFAULT_MODEL_CACHE_DIR),
    source_model: str = DEFAULT_GLINER_SOURCE_MODEL,
    local_files_only: bool = False,
) -> list[Finding]:
    """Apply GLiNER to all available sections."""

    model = load_gliner_model(model_name, cache_dir, source_model, local_files_only)
    findings: list[Finding] = []
    for section_name, section_text in sections.items():
        findings.extend(
            analyze_gliner_section(
                section_name,
                section_text,
                labels=labels,
                threshold=threshold,
                model_name=model_name,
                cache_dir=cache_dir,
                source_model=source_model,
                local_files_only=local_files_only,
                model=model,
            )
        )
    return findings
