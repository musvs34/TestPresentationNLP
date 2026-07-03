from pathlib import Path

from compliance_nlp.config import load_generic_detection_rules, load_whitelist_terms
from compliance_nlp.pipeline import analyze_text


def _write_central_rules(path: Path) -> None:
    path.write_text(
        "rule_id,rule_scope,regulatory_family,section_scope,category,label,terms,synonyms,alert_level,severity,base_score,fuzzy_threshold,applies_whitelist\n"
        "SANTE_DIABETE,article9,rgpd_article_9,document,sante,Diabete,diabete|diabetique,insuline|glycemie,interdit,critical,0.90,0.86,true\n"
        "POLITIQUE,article9,rgpd_article_9,document,opinions_politiques,Politique,engagement politique|militant politique,parti politique,interdit,critical,0.88,0.86,true\n",
        encoding="utf-8",
    )


def test_article9_detects_exact_sensitive_term_from_central_rules(tmp_path: Path) -> None:
    csv_path = tmp_path / "generic_detection_rules.csv"
    _write_central_rules(csv_path)

    result = analyze_text(
        "sample.pdf",
        "sample.pdf",
        "Le client indique dans la zone libre qu'il est diabetique.",
        generic_rules=load_generic_detection_rules(csv_path),
    )

    finding = next(finding for finding in result.findings if finding.rule_id == "SANTE_DIABETE")
    assert finding.code == "article9_sante"
    assert finding.rule_scope == "article9"
    assert finding.regulatory_family == "rgpd_article_9"
    assert finding.category == "sante"
    assert finding.detection_type == "exact"
    assert finding.score == 0.9


def test_article9_detects_synonym_from_central_rules(tmp_path: Path) -> None:
    csv_path = tmp_path / "generic_detection_rules.csv"
    _write_central_rules(csv_path)

    result = analyze_text(
        "sample.pdf",
        "sample.pdf",
        "Observation conseiller: traitement par insuline signale par l'adherent.",
        generic_rules=load_generic_detection_rules(csv_path),
    )

    finding = next(finding for finding in result.findings if finding.rule_id == "SANTE_DIABETE")
    assert finding.detection_type == "synonym"
    assert finding.matched_term == "insuline"


def test_article9_detects_spelling_error_from_central_rules(tmp_path: Path) -> None:
    csv_path = tmp_path / "generic_detection_rules.csv"
    _write_central_rules(csv_path)

    result = analyze_text(
        "sample.pdf",
        "sample.pdf",
        "Le souscripteur precise etre diabettique depuis plusieurs annees.",
        generic_rules=load_generic_detection_rules(csv_path),
    )

    finding = next(finding for finding in result.findings if finding.rule_id == "SANTE_DIABETE")
    assert finding.detection_type == "fuzzy"
    assert finding.matched_term == "diabettique"
    assert finding.score >= 0.65


def test_article9_applies_whitelist_from_central_rules(tmp_path: Path) -> None:
    rules_path = tmp_path / "generic_detection_rules.csv"
    rules_path.write_text(
        "rule_id,rule_scope,regulatory_family,section_scope,category,label,terms,synonyms,alert_level,severity,base_score,fuzzy_threshold,applies_whitelist\n"
        "SANTE,article9,rgpd_article_9,document,sante,Sante,sante,,interdit,critical,0.80,0.90,true\n",
        encoding="utf-8",
    )
    whitelist_path = tmp_path / "article9_whitelist.csv"
    whitelist_path.write_text(
        "expression,reason\n"
        "sante financiere,Expression non medicale\n",
        encoding="utf-8",
    )

    result = analyze_text(
        "sample.pdf",
        "sample.pdf",
        "La sante financiere du contrat reste correcte.",
        generic_rules=load_generic_detection_rules(rules_path),
        whitelist_terms=load_whitelist_terms(whitelist_path),
    )

    assert not [finding for finding in result.findings if finding.rule_scope == "article9"]
    assert result.metadata["whitelist_ignored_count"] == 1
    ignored = result.metadata["whitelist_ignored_findings"][0]
    assert ignored["whitelist_expression"] == "sante financiere"
    assert ignored["finding"]["matched_term"] == "sante"


def test_pipeline_applies_whitelist_to_regex_branch(tmp_path: Path) -> None:
    whitelist_path = tmp_path / "article9_whitelist.csv"
    whitelist_path.write_text(
        "expression,reason\n"
        "contact test@example.com,Adresse de test autorisee\n",
        encoding="utf-8",
    )

    result = analyze_text(
        "sample.pdf",
        "sample.pdf",
        "Contact test@example.com.",
        whitelist_terms=load_whitelist_terms(whitelist_path),
        enabled_branches=("regex",),
    )

    assert result.findings == []
    assert result.metadata["regex_finding_count"] == 0
    assert result.metadata["raw_finding_count_by_engine"] == {"regex": 1}
    assert result.metadata["whitelist_ignored_count_by_engine"] == {"regex": 1}
    ignored = result.metadata["whitelist_ignored_findings"][0]
    assert ignored["finding"]["detection_engine"] == "regex"
    assert ignored["finding"]["matched_term"] == "test@example.com"
