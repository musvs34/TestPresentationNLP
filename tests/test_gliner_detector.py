from compliance_nlp.gliner_detector import analyze_gliner_documents, analyze_gliner_section


class FakeGlinerModel:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def predict_entities(self, text, labels, threshold):  # type: ignore[no-untyped-def]
        self.calls.append(tuple(labels))
        if tuple(labels) == ("ideologie politique", "position politique"):
            return [
                {
                    "start": 42,
                    "end": 56,
                    "text": "extreme droite",
                    "label": "ideologie politique",
                    "score": 0.5536,
                }
            ]
        return []


def test_gliner_accepts_label_groups_and_runs_each_group() -> None:
    model = FakeGlinerModel()

    findings = analyze_gliner_section(
        "document",
        "c'est une personne qui siege a l'assemblee et a une vision a l'extreme droite",
        labels={
            "sante": ("maladie", "pathologie"),
            "politique": ("ideologie politique", "position politique"),
        },
        model=model,
    )

    assert model.calls == [
        ("maladie", "pathologie"),
        ("ideologie politique", "position politique"),
    ]
    assert len(findings) == 1
    assert findings[0].matched_term == "extreme droite"
    assert findings[0].title == "ideologie politique"
    assert findings[0].gliner_score == 0.55


def test_gliner_keeps_single_label_list_compatibility() -> None:
    model = FakeGlinerModel()

    analyze_gliner_section(
        "document",
        "texte",
        labels=("donnee de sante",),
        model=model,
    )

    assert model.calls == [("donnee de sante",)]


class FakeBatchGlinerModel:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], tuple[str, ...], int]] = []

    def inference(self, texts, labels, threshold, batch_size):  # type: ignore[no-untyped-def]
        self.calls.append((tuple(texts), tuple(labels), batch_size))
        return [
            [{"text": text, "label": labels[0], "score": 0.8}]
            for text in texts
        ]


def test_gliner_batches_documents_while_preserving_label_groups() -> None:
    model = FakeBatchGlinerModel()

    results = analyze_gliner_documents(
        [("document", "alpha"), ("document", "beta"), ("document", "gamma")],
        labels={"groupe_1": ("label 1",), "groupe_2": ("label 2",)},
        batch_size=2,
        model=model,
    )

    assert len(model.calls) == 4
    assert [len(findings) for findings in results] == [2, 2, 2]
    assert {finding.title for finding in results[0]} == {"label 1", "label 2"}
