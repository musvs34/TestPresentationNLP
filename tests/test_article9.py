from pathlib import Path

from compliance_nlp.config import load_article9_terms, load_whitelist_terms
from compliance_nlp.pipeline import analyze_text


def _write_article9_terms(path: Path) -> None:
    path.write_text(
        "rule_id,category,label,terms,synonyms,alert_level,base_score,fuzzy_threshold\n"
        "SANTE_DIABETE,sante,Diabete,diabete|diabetique,insuline|glycemie,interdit,0.90,0.86\n"
        "POLITIQUE,opinions_politiques,Politique,engagement politique|militant politique,parti politique,interdit,0.88,0.86\n",
        encoding="utf-8",
    )


def test_article9_detects_exact_sensitive_term(tmp_path: Path) -> None:
    csv_path = tmp_path / "article9_terms.csv"
    _write_article9_terms(csv_path)

    article9_terms = load_article9_terms(csv_path)
    result = analyze_text(
        "sample.pdf",
        "sample.pdf",
        "Le client indique dans la zone libre qu'il est diabetique.",
        article9_terms=article9_terms,
    )

    finding = next(finding for finding in result.findings if finding.rule_id == "SANTE_DIABETE")
    assert finding.category == "sante"
    assert finding.detection_type == "exact"
    assert finding.score == 0.9


def test_article9_detects_synonym(tmp_path: Path) -> None:
    csv_path = tmp_path / "article9_terms.csv"
    _write_article9_terms(csv_path)

    article9_terms = load_article9_terms(csv_path)
    result = analyze_text(
        "sample.pdf",
        "sample.pdf",
        "Observation conseiller: traitement par insuline signale par l'adherent.",
        article9_terms=article9_terms,
    )

    finding = next(finding for finding in result.findings if finding.rule_id == "SANTE_DIABETE")
    assert finding.detection_type == "synonym"
    assert finding.matched_term == "insuline"


def test_article9_detects_spelling_error(tmp_path: Path) -> None:
    csv_path = tmp_path / "article9_terms.csv"
    _write_article9_terms(csv_path)

    article9_terms = load_article9_terms(csv_path)
    result = analyze_text(
        "sample.pdf",
        "sample.pdf",
        "Le souscripteur precise etre diabettique depuis plusieurs annees.",
        article9_terms=article9_terms,
    )

    finding = next(finding for finding in result.findings if finding.rule_id == "SANTE_DIABETE")
    assert finding.detection_type == "fuzzy"
    assert finding.matched_term == "diabettique"
    assert finding.score >= 0.65


def test_article9_applies_whitelist(tmp_path: Path) -> None:
    terms_path = tmp_path / "article9_terms.csv"
    terms_path.write_text(
        "rule_id,category,label,terms,synonyms,alert_level,base_score,fuzzy_threshold\n"
        "SANTE,sante,Sante,sante,,interdit,0.80,0.90\n",
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
        article9_terms=load_article9_terms(terms_path),
        whitelist_terms=load_whitelist_terms(whitelist_path),
    )

    assert not [finding for finding in result.findings if finding.code.startswith("article9_")]
