from pathlib import Path

from compliance_nlp.config import (
    load_generic_detection_rules,
    load_spacy_synonym_map,
    refresh_spacy_synonyms_from_forbidden_words,
)
from compliance_nlp.generic import analyze_generic_section
from compliance_nlp.linguistic import _synonyms_for_rule_terms
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


def test_loads_forbidden_words_dpo_format(tmp_path: Path) -> None:
    csv_path = tmp_path / "Mots_interdits.csv"
    csv_path.write_text(
        "Catégorie;Terme interdit;Justification\n"
        "Données sensibles (article 9 RGPD);dépression;Données de santé (art. 9 RGPD)\n"
        "Jugements de valeur et commentaires subjectifs;menteur;Commentaire subjectif, non objectivé\n",
        encoding="utf-8",
    )

    rules = load_generic_detection_rules(csv_path)

    assert len(rules) == 2
    assert rules[0].rule_id == "mots_interdits_001_depression"
    assert rules[0].rule_scope == "article9"
    assert rules[0].regulatory_family == "rgpd_article_9"
    assert rules[0].section_scope == ("document",)
    assert rules[0].category == "donnees_sensibles_article_9_rgpd"
    assert rules[0].label == "Données de santé (art. 9 RGPD)"
    assert rules[0].terms == ("dépression",)
    assert rules[0].applies_whitelist is True
    assert rules[1].rule_scope == "general"
    assert rules[1].severity == "high"


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


def test_loads_spacy_synonyms_from_separate_file(tmp_path: Path) -> None:
    csv_path = tmp_path / "spacy_synonyms.csv"
    csv_path.write_text(
        "term,synonyms\n"
        "garantie,assure|certain\n",
        encoding="utf-8",
    )

    synonym_map = load_spacy_synonym_map(csv_path)

    assert synonym_map == {"garantie": ("assure", "certain")}


def test_refreshes_spacy_synonyms_from_forbidden_words(tmp_path: Path) -> None:
    forbidden_words_path = tmp_path / "Mots_interdits.csv"
    forbidden_words_path.write_text(
        "Catégorie;Terme interdit;Justification\n"
        "Données sensibles (article 9 RGPD);dépression;Données de santé\n"
        "Jugements de valeur;menteur;Commentaire subjectif\n",
        encoding="utf-8",
    )
    synonyms_path = tmp_path / "spacy_synonyms.csv"
    synonyms_path.write_text(
        "term,synonyms\n"
        "depression,trouble depressif|antidepresseur\n"
        "ancien terme,synonyme obsolete\n",
        encoding="utf-8",
    )

    count = refresh_spacy_synonyms_from_forbidden_words(
        forbidden_words_path,
        synonyms_path,
    )

    assert count == 2
    assert synonyms_path.read_text(encoding="utf-8").splitlines() == [
        "term,synonyms",
        "depression,trouble depressif|antidepresseur",
        "menteur,",
    ]


def test_refreshes_spacy_synonyms_from_cached_jeuxdemots(tmp_path: Path) -> None:
    forbidden_words_path = tmp_path / "Mots_interdits.csv"
    forbidden_words_path.write_text(
        "Catégorie;Terme interdit;Justification\n"
        "Jugements de valeur;menteur;Commentaire subjectif\n",
        encoding="utf-8",
    )
    synonyms_path = tmp_path / "spacy_synonyms.csv"
    store_path = tmp_path / "jeuxdemots"
    store_path.mkdir()
    (store_path / "menteur.html").write_text(
        """
        // DUMP pour le terme 'menteur' (eid=1)
        e;1;'menteur';1;100
        e;2;'hâbleur';1;90
        e;3;'imposteur';1;80
        e;4;'en:liar';1;70
        r;10;1;2;5;172;1;1
        r;11;1;3;5;160;0.9;2
        r;12;1;4;5;150;0.8;3
        """,
        encoding="utf-8",
    )

    count = refresh_spacy_synonyms_from_forbidden_words(
        forbidden_words_path,
        synonyms_path,
        jeuxdemots_store_path=store_path,
        enrich_with_jeuxdemots=True,
        allow_network=False,
    )

    assert count == 1
    assert synonyms_path.read_text(encoding="utf-8").splitlines() == [
        "term,synonyms",
        "menteur,hableur|imposteur",
    ]


def test_spacy_synonyms_are_derived_from_rule_terms_not_rule_synonyms(tmp_path: Path) -> None:
    rules_path = tmp_path / "generic_detection_rules.csv"
    _write_generic_rules(rules_path)
    rules = load_generic_detection_rules(rules_path)
    synonym_map = {"garantie": ("assure", "certain")}

    resolved = _synonyms_for_rule_terms(rules[0], synonym_map)

    assert resolved == ("assure", "certain")

    synonym_map = {}
    resolved = _synonyms_for_rule_terms(rules[0], synonym_map)

    assert resolved == ()


def test_pipeline_uses_default_generic_rules() -> None:
    text = """
    Le client signale une depression et des antecedents medicaux.
    Le commentaire indique aussi que le client est menteur.
    """

    result = analyze_text("sample.pdf", "sample.pdf", text)

    matched_terms = {finding.matched_term for finding in result.findings}
    assert "dépression" in matched_terms or "depression" in matched_terms
    assert "menteur" in matched_terms
    assert {finding.detection_engine for finding in result.findings} == {"generic"}


def test_pipeline_can_enable_spacy_branch_without_breaking_generic() -> None:
    text = """
    Le commentaire indique que le client est menteur.
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


def test_pipeline_can_enable_gliner_branch_without_breaking_generic() -> None:
    text = """
    Le commentaire indique que le client est menteur.
    """

    result = analyze_text(
        "sample.pdf",
        "sample.pdf",
        text,
        enabled_branches=("generic", "gliner"),
        gliner_model="modele_gliner_absent",
        gliner_labels=("donnee de sante",),
    )

    assert any(finding.detection_engine == "generic" for finding in result.findings)
    assert "gliner" in result.metadata["branch_errors"]
    assert result.metadata["gliner_labels"] == ["donnee de sante"]


def test_pipeline_can_enable_regex_branch() -> None:
    result = analyze_text(
        "sample.pdf",
        "sample.pdf",
        "Contact 06-05.01 0404 et joignable test@yahoo.Fr.",
        enabled_branches=("regex",),
    )

    assert result.metadata["regex_finding_count"] == 2
    assert result.metadata["regex_max_score"] == 0.95
    assert {finding.rule_id for finding in result.findings} == {"EMAIL_ADDRESS", "PHONE_NUMBER_FR"}
    assert {finding.detection_engine for finding in result.findings} == {"regex"}
