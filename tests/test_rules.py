from compliance_nlp.pipeline import analyze_text


def test_detects_forbidden_words_on_full_document() -> None:
    text = """
    Le client signale une depression ancienne.
    Le commentaire interne indique que le client est menteur.
    """

    result = analyze_text("sample.pdf", "sample.pdf", text)

    matches = {(finding.section, finding.matched_term, finding.rule_scope) for finding in result.findings}
    assert ("document", "dépression", "article9") in matches or (
        "document",
        "depression",
        "article9",
    ) in matches
    assert ("document", "menteur", "general") in matches


def test_pipeline_exposes_only_document_section() -> None:
    result = analyze_text(
        "sample.pdf",
        "sample.pdf",
        "Contact 06-05.01 0404 et client agressif.",
        enabled_branches=("generic", "regex"),
    )

    assert set(result.sections) == {"document"}
    assert result.metadata["analysis_scope"] == "document"
    assert {finding.section for finding in result.findings} == {"document"}
