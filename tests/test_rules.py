from compliance_nlp.pipeline import analyze_text


def test_detects_imprecise_beneficiary_clause() -> None:
    text = """
    7. Beneficiaires
    Je souhaite que le capital revienne a la personne qui sera la plus presente
    pour moi au moment venu, sinon mes proches.
    8. Declarations
    9. Conseil et Recommandation
    RAS
    10. Signatures
    """

    result = analyze_text("sample.pdf", "sample.pdf", text)

    assert any(finding.code == "beneficiary_clause_imprecise" for finding in result.findings)


def test_detects_non_professional_advice() -> None:
    text = """
    7. Beneficiaires
    Mes heritiers.
    8. Declarations
    9. Conseil et Recommandation
    Je lui ai dit de foncer sans trop reflechir car ce contrat est top.
    Les risques ne sont pas un vrai sujet ici.
    10. Signatures
    """

    result = analyze_text("sample.pdf", "sample.pdf", text)

    codes = {finding.code for finding in result.findings}
    assert "advice_unprofessional_wording" in codes
    assert "advice_risk_minimization" in codes


def test_detects_capacity_mismatch() -> None:
    text = """
    7. Beneficiaires
    Mes parents.
    8. Declarations
    9. Conseil et Recommandation
    L'effort represente une part tres importante du revenu disponible
    et depasse ses capacites actuelles.
    10. Signatures
    """

    result = analyze_text("sample.pdf", "sample.pdf", text)

    assert any(
        finding.code == "advice_above_financial_capacity" for finding in result.findings
    )


def test_detects_default_formula_and_spelling_quality_issue() -> None:
    text = """
    7. Beneficiaires
    Mes enfants.
    8. Declarations
    9. Conseil et Recommandation
    La cliente ne comprand pas bien les diferences entre les suport.
    Une formule par defaut a ete mise en place pour aller plus vite.
    Le dossier est finaliser sur cette base standart.
    10. Signatures
    """

    result = analyze_text("sample.pdf", "sample.pdf", text)

    codes = {finding.code for finding in result.findings}
    assert "advice_default_formula_due_to_client_confusion" in codes
    assert "advice_spelling_quality_issue" in codes


def test_detects_central_forbidden_rules_in_beneficiary_and_advice_sections() -> None:
    text = """
    7. Beneficiaires
    Mes proches par parts egales.
    8. Declarations
    9. Conseil et Recommandation
    Une formule par defaut a ete appliquee.
    Ce placement est sans risque.
    10. Signatures
    """

    result = analyze_text("sample.pdf", "sample.pdf", text)

    matched_terms = {
        (finding.section, finding.matched_term, finding.alert_level)
        for finding in result.findings
    }
    assert ("beneficiaires", "proches", "ambigue") in matched_terms
    assert ("conseil", "par defaut", "ambigue") in matched_terms
    assert ("conseil", "sans risque", "interdit") in matched_terms


def test_section_extraction_is_case_insensitive() -> None:
    text = """
    7. BENEFICIAIRES
    Mes proches par parts egales.
    8. DECLARATIONS
    9. CONSEIL ET RECOMMANDATION
    Il faut foncer.
    10. SIGNATURES
    """

    result = analyze_text("sample.pdf", "sample.pdf", text)

    matched_terms = {(finding.section, finding.matched_term) for finding in result.findings}
    assert ("beneficiaires", "proches") in matched_terms
    assert ("conseil", "foncer") in matched_terms
