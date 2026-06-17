from pathlib import Path

from compliance_nlp.config import load_generic_detection_rules
from compliance_nlp.generic import analyze_generic_section
from compliance_nlp.pipeline import analyze_text


def _write_generic_rules(path: Path) -> None:
    path.write_text(
        "rule_id,section_scope,category,label,terms,synonyms,alert_level,severity,base_score,fuzzy_threshold\n"
        "GEN_FORBIDDEN,conseil,mot_interdit,Terme interdit,sans risque|garantie,assure|certain,interdit,high,0.90,0.86\n"
        "GEN_BENEF,beneficiaires,clause_beneficiaire,Clause imprecise,mes proches,,ambigue,low,0.65,0.86\n",
        encoding="utf-8",
    )


def test_loads_generic_detection_rules(tmp_path: Path) -> None:
    csv_path = tmp_path / "generic_detection_rules.csv"
    _write_generic_rules(csv_path)

    rules = load_generic_detection_rules(csv_path)

    assert len(rules) == 2
    assert rules[0].rule_id == "GEN_FORBIDDEN"
    assert rules[0].rule_scope == "general"
    assert rules[0].regulatory_family == "general"
    assert rules[0].section_scope == ("conseil",)
    assert rules[0].terms == ("sans risque", "garantie")
    assert rules[0].synonyms == ("assure", "certain")


def test_generic_detector_matches_exact_phrase(tmp_path: Path) -> None:
    csv_path = tmp_path / "generic_detection_rules.csv"
    _write_generic_rules(csv_path)

    findings = analyze_generic_section(
        "conseil",
        "Ce placement est sans risque pour le client.",
        load_generic_detection_rules(csv_path),
    )

    assert findings[0].rule_id == "GEN_FORBIDDEN"
    assert findings[0].rule_scope == "general"
    assert findings[0].detection_type == "exact"
    assert findings[0].matched_term == "sans risque"


def test_generic_detector_matches_synonym(tmp_path: Path) -> None:
    csv_path = tmp_path / "generic_detection_rules.csv"
    _write_generic_rules(csv_path)

    findings = analyze_generic_section(
        "conseil",
        "Le conseiller presente le support comme certain.",
        load_generic_detection_rules(csv_path),
    )

    assert findings[0].rule_id == "GEN_FORBIDDEN"
    assert findings[0].detection_type == "synonym"
    assert findings[0].matched_term == "certain"


def test_generic_detector_matches_spelling_error(tmp_path: Path) -> None:
    csv_path = tmp_path / "generic_detection_rules.csv"
    _write_generic_rules(csv_path)

    findings = analyze_generic_section(
        "conseil",
        "Le capital est garentie par le contrat.",
        load_generic_detection_rules(csv_path),
    )

    assert findings[0].rule_id == "GEN_FORBIDDEN"
    assert findings[0].detection_type == "fuzzy"
    assert findings[0].matched_term == "garentie"


def test_pipeline_uses_default_generic_rules() -> None:
    text = """
    7. Beneficiaires
    Mes proches par parts egales.
    8. Declarations
    9. Conseil et Recommandation
    Ce placement est sans risque.
    10. Signatures
    """

    result = analyze_text("sample.pdf", "sample.pdf", text)

    rule_ids = {finding.rule_id for finding in result.findings}
    assert "beneficiary_clause_imprecise" in rule_ids
    assert "forbidden_sans_risque" in rule_ids
    assert {finding.detection_engine for finding in result.findings} == {"generic"}


def test_pipeline_can_enable_spacy_branch_without_breaking_generic() -> None:
    text = """
    9. Conseil et Recommandation
    Ce placement est sans risque.
    10. Signatures
    """

    result = analyze_text(
        "sample.pdf",
        "sample.pdf",
        text,
        enabled_branches=("generic", "spacy"),
        spacy_model="modele_francais_absent",
    )

    assert any(finding.detection_engine == "generic" for finding in result.findings)
    assert "spacy" in result.metadata["branch_errors"]
