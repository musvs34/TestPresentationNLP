"""GLiNER-based configurable named-entity detection branch."""

from __future__ import annotations

from functools import lru_cache

from .models import Finding
from .text_utils import compact_text, normalize_for_matching, shorten


DEFAULT_GLINER_MODEL = "urchade/gliner_multi-v2.1"
DEFAULT_GLINER_THRESHOLD = 0.50
DEFAULT_GLINER_LABELS = (
    "donnee de sante",
    "opinion politique",
    "conviction religieuse",
    "appartenance syndicale",
    "orientation sexuelle",
    "origine ethnique",
    "donnee genetique",
    "donnee biometrique",
    "clause beneficiaire imprecise",
    "conseil non professionnel",
    "promesse de performance",
)


@lru_cache(maxsize=2)
def load_gliner_model(model_name: str = DEFAULT_GLINER_MODEL):  # type: ignore[no-untyped-def]
    """Load and cache the configured GLiNER model."""

    try:
        from gliner import GLiNER
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "The GLiNER branch requires the 'gliner' package. Install optional NLP "
            "dependencies before enabling it."
        ) from exc

    try:
        return GLiNER.from_pretrained(model_name)
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
    labels = labels or DEFAULT_GLINER_LABELS
    return tuple(label.strip() for label in labels if label and label.strip())


def analyze_gliner_section(
    section_name: str,
    section_text: str,
    labels: list[str] | tuple[str, ...] | None = None,
    threshold: float = DEFAULT_GLINER_THRESHOLD,
    model_name: str = DEFAULT_GLINER_MODEL,
    model=None,  # type: ignore[no-untyped-def]
) -> list[Finding]:
    """Apply GLiNER zero-shot entity recognition to one section."""

    compact_section = compact_text(section_text)
    if not compact_section:
        return []

    resolved_labels = _normalize_labels(labels)
    if not resolved_labels:
        return []

    model = model or load_gliner_model(model_name)
    entities = model.predict_entities(
        compact_section,
        list(resolved_labels),
        threshold=threshold,
    )

    findings: list[Finding] = []
    for entity in entities:
        label = str(entity.get("label") or "").strip()
        matched_text = str(entity.get("text") or "").strip()
        score = entity.get("score")
        if not label or not matched_text:
            continue
        numeric_score = round(float(score), 2) if score is not None else None
        code = _label_to_code(label)

        findings.append(
            Finding(
                code=code,
                severity="medium",
                section=section_name,
                title=label,
                detail=f"GLiNER detected '{matched_text}' as '{label}'.",
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
        )

    return findings


def analyze_gliner_sections(
    sections: dict[str, str],
    labels: list[str] | tuple[str, ...] | None = None,
    threshold: float = DEFAULT_GLINER_THRESHOLD,
    model_name: str = DEFAULT_GLINER_MODEL,
) -> list[Finding]:
    """Apply GLiNER to all available sections."""

    model = load_gliner_model(model_name)
    findings: list[Finding] = []
    for section_name, section_text in sections.items():
        findings.extend(
            analyze_gliner_section(
                section_name,
                section_text,
                labels=labels,
                threshold=threshold,
                model_name=model_name,
                model=model,
            )
        )
    return findings
