from __future__ import annotations

import csv
import html
import struct
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "specifications"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCX_PATH = OUT_DIR / "specification_complete_projet_compliance_nlp.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(2048)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        except csv.Error:
            dialect = csv.excel
        return list(csv.DictReader(handle, dialect=dialect))


FORBIDDEN_ROWS = read_csv_rows(ROOT / "configs" / "Mots_interdits.csv")
WHITELIST_ROWS = read_csv_rows(ROOT / "configs" / "article9_whitelist.csv")
SPACY_SYNONYM_ROWS = read_csv_rows(ROOT / "configs" / "spacy_synonyms.csv")
TEST_CASE_ROWS = read_csv_rows(ROOT / "configs" / "test_cases.csv")

category_counter = Counter(
    (row.get("Catégorie") or row.get("Categorie") or "Non catégorisé").strip()
    for row in FORBIDDEN_ROWS
)

GLINER_LABELS = [
    "donnee de sante",
    "maladie",
    "pathologie",
    "autisme",
    "handicap",
    "trouble du neurodeveloppement",
    "etat de sante",
    "condition medicale",
    "probleme de sante",
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
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=False)


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        return 1200, 700
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def run(text: str, bold: bool = False, italic: bool = False) -> str:
    rpr = ""
    if bold or italic:
        rpr = "<w:rPr>"
        if bold:
            rpr += "<w:b/>"
        if italic:
            rpr += "<w:i/>"
        rpr += "</w:rPr>"
    return f'<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def paragraph(text: str = "", style: str | None = None, bold: bool = False, italic: bool = False) -> str:
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{ppr}{run(text, bold=bold, italic=italic)}</w:p>"


def heading(text: str, level: int = 1) -> str:
    return paragraph(text, style=f"Heading{level}")


def bullet(text: str) -> str:
    return (
        '<w:p><w:pPr><w:pStyle w:val="ListBullet"/>'
        '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>'
        f"{run(text)}</w:p>"
    )


def page_break() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def table(headers: list[str], rows: list[list[object]]) -> str:
    xml = [
        '<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/>'
        '<w:tblW w:w="0" w:type="auto"/>'
        '<w:tblCellMar><w:top w:w="80" w:type="dxa"/><w:left w:w="80" w:type="dxa"/>'
        '<w:bottom w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar>'
        "</w:tblPr>"
    ]
    for index, row in enumerate([headers, *rows]):
        xml.append("<w:tr>")
        for cell in row:
            shade = '<w:shd w:fill="D9EAF7"/>' if index == 0 else ""
            xml.append(f"<w:tc><w:tcPr>{shade}</w:tcPr>{paragraph(cell, bold=index == 0)}</w:tc>")
        xml.append("</w:tr>")
    xml.append("</w:tbl>")
    return "".join(xml)


image_rels: list[tuple[str, str, Path]] = []


def image(path: Path, width_inches: float = 6.5) -> str:
    if not path.exists():
        return paragraph(f"Image non disponible : {path.name}", italic=True)
    rel_id = f"rIdImg{len(image_rels) + 1}"
    target_name = f"image{len(image_rels) + 1}.png"
    image_rels.append((rel_id, target_name, path))
    width_px, height_px = png_size(path)
    cx = int(width_inches * 914400)
    cy = int(cx * height_px / width_px)
    docpr_id = len(image_rels) + 10
    return f"""
<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:drawing>
<wp:inline distT="0" distB="0" distL="0" distR="0">
<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{docpr_id}" name="{esc(path.stem)}"/>
<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
<pic:pic>
<pic:nvPicPr><pic:cNvPr id="0" name="{esc(path.name)}"/><pic:cNvPicPr/></pic:nvPicPr>
<pic:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
</pic:pic>
</a:graphicData></a:graphic>
</wp:inline></w:drawing></w:r></w:p>
"""


def body_content() -> list[str]:
    functional_img = OUT_DIR / "architecture_fonctionnelle.png"
    technical_img = OUT_DIR / "architecture_technique.png"
    branch_img = OUT_DIR / "specificites_branches.png"

    content: list[str] = []
    content.append(paragraph("Spécification complète du projet Compliance NLP", style="Title"))
    content.append(paragraph(f"Document fonctionnel et technique - généré le {date.today().strftime('%d/%m/%Y')}", italic=True))
    content.append(paragraph("Projet : pocComplianceNLP"))
    content.append(paragraph("Objet : détection d'alertes de conformité dans des documents ou textes d'assurance vie à l'aide de règles métier, de traitements linguistiques et de modèles NLP locaux."))

    content.append(heading("1. Synthèse exécutive"))
    content.append(paragraph(
        "Le projet met en place une chaîne d'analyse NLP locale destinée à repérer dans des textes libres ou des documents PDF des formulations présentant un risque de conformité. "
        "Les risques couverts incluent notamment les données sensibles Article 9 RGPD, les jugements de valeur, les informations personnelles non nécessaires et les données structurées sensibles."
    ))
    content.append(paragraph(
        "L'approche repose sur quatre branches complémentaires : une branche de règles métier explicables, une branche linguistique spaCy, une branche de reconnaissance conceptuelle GLiNER et une branche Regex pour les formats structurés. "
        "Chaque branche produit des alertes comparables avec score, catégorie, justification, preuve textuelle et moteur source."
    ))

    content.append(heading("2. Spécification fonctionnelle"))
    content.append(heading("2.1 Objectifs métier", 2))
    for item in [
        "Détecter automatiquement des termes ou formulations à risque dans les documents de souscription et d'adhésion.",
        "Expliquer chaque alerte par une catégorie métier et une justification issue du référentiel.",
        "Distinguer les alertes réglementaires fortes des suspicions nécessitant une revue humaine.",
        "Comparer plusieurs stratégies de reconnaissance sur les mêmes cas de test.",
        "Limiter les faux positifs via une whitelist métier, en particulier pour les expressions Article 9 ambiguës.",
    ]:
        content.append(bullet(item))

    content.append(heading("2.2 Périmètre fonctionnel", 2))
    content.append(table(
        ["Élément", "Description"],
        [
            ["Entrées", "Documents PDF présents dans data/raw, textes issus des notebooks, cas de test centralisés dans configs/test_cases.csv."],
            ["Sorties", "Objets DocumentAnalysis contenant sections, findings et métadonnées ; DataFrame de comparaison dans les notebooks."],
            ["Référentiel principal", f"configs/Mots_interdits.csv avec {len(FORBIDDEN_ROWS)} entrées : catégorie, terme interdit, justification."],
            ["Whitelist", f"configs/article9_whitelist.csv avec {len(WHITELIST_ROWS)} expressions neutralisées pour éviter des faux positifs."],
            ["Cas de test", f"configs/test_cases.csv avec {len(TEST_CASE_ROWS)} cas de validation fonctionnelle."],
            ["Exécution", "Scripts Python, notebooks d'exploration et notebook 03e pour la comparaison globale des branches."],
        ],
    ))

    content.append(heading("2.3 Familles de règles métier", 2))
    content.append(table(
        ["Famille", "Nombre de termes", "Finalité métier"],
        [
            [category or "Non catégorisé", count, "Détection et justification d'une alerte de conformité."]
            for category, count in category_counter.items()
        ],
    ))

    content.append(heading("2.4 Principe de décision métier", 2))
    for item in [
        "Le texte est normalisé afin de fiabiliser la comparaison, sans perdre l'extrait original utilisé comme preuve.",
        "Chaque branche tente de reconnaître un risque selon sa propre logique.",
        "Une alerte est produite si un risque est détecté et si l'expression n'est pas neutralisée par la whitelist.",
        "Le score indique le niveau de confiance de la branche, pas une décision automatique définitive.",
        "La revue humaine reste nécessaire pour qualifier les alertes sensibles ou ambiguës.",
    ]:
        content.append(bullet(item))

    content.append(heading("2.5 Architecture fonctionnelle", 2))
    content.append(image(functional_img, width_inches=6.9))

    content.append(page_break())
    content.append(heading("3. Description détaillée des 4 branches"))
    content.append(heading("3.1 Vue comparative", 2))
    content.append(image(branch_img, width_inches=6.9))

    content.append(heading("3.2 Branche Generic - règles métier explicables", 2))
    content.append(paragraph(
        "La branche Generic est le socle déterministe du dispositif. Elle lit les termes interdits depuis le référentiel métier, applique les catégories et justifications configurées, puis retourne une alerte lorsqu'un terme ou une variante acceptable est reconnue."
    ))
    content.append(table(
        ["Aspect", "Description"],
        [
            ["Entrée", "Texte normalisé du document complet."],
            ["Référentiel", "configs/Mots_interdits.csv."],
            ["Méthodes de détection", "Exact match, racine simple, fuzzy matching, synonymes portés par les règles techniques historiques si présents."],
            ["Whitelist", "Appliquée pour les règles Article 9 afin de supprimer les expressions métier non sensibles."],
            ["Score", "Base 0,90 pour Article 9, 0,85 pour les autres règles ; pénalités selon synonymie, racine ou fuzzy."],
            ["Cas d'usage", "Contrôle robuste et auditable des termes attendus par le métier."],
            ["Limite", "Peu de compréhension sémantique au-delà du terme ou de ses variantes textuelles."],
        ],
    ))

    content.append(heading("3.3 Branche spaCy - reconnaissance linguistique", 2))
    content.append(paragraph(
        "La branche spaCy complète la branche Generic avec une analyse linguistique française. Elle exploite les lemmes, les racines et des synonymes contrôlés dans un fichier séparé afin de détecter des variantes grammaticales ou lexicales d'un terme métier."
    ))
    content.append(table(
        ["Aspect", "Description"],
        [
            ["Modèle", "fr_core_news_md chargé depuis le modelStore local."],
            ["Référentiels", f"Mots interdits + configs/spacy_synonyms.csv ({len(SPACY_SYNONYM_ROWS)} entrées)."],
            ["Méthodes de détection", "Exact match, lemmatisation, racine, fuzzy matching et synonymes contrôlés."],
            ["Exemple", "Le référentiel contient agressif ; spaCy peut rapprocher agressive/agressives via la lemmatisation."],
            ["Score", "Base de la règle avec pénalités : lemme, racine, synonyme ou fuzzy."],
            ["Cas d'usage", "Détecter les formes fléchies, accords et variantes proches sans multiplier les lignes du référentiel métier."],
            ["Limite", "Dépend de la qualité du modèle linguistique et du fichier de synonymes."],
        ],
    ))

    content.append(heading("3.4 Branche GLiNER - reconnaissance de concepts", 2))
    content.append(paragraph(
        "La branche GLiNER détecte des entités ou concepts à partir d'une liste de labels métier. Elle est utile lorsque le risque n'apparaît pas forcément sous la forme exacte du référentiel, mais sous une formulation conceptuellement proche."
    ))
    content.append(table(
        ["Aspect", "Description"],
        [
            ["Modèle", "gliner_multi-v2.1 chargé depuis le modelStore local."],
            ["Labels", f"{len(GLINER_LABELS)} labels configurés : santé, pathologie, opinion politique, conviction religieuse, clause imprécise, promesse de performance..."],
            ["Méthode de détection", "Prédiction d'entités sur le texte avec seuil de confiance."],
            ["Seuil", "0,50 dans le notebook de comparaison."],
            ["Score", "Score renvoyé par le modèle, arrondi et stocké dans gliner_score."],
            ["Cas d'usage", "Repérer des concepts ou entités métier sans écrire toutes les formulations possibles."],
            ["Limite", "Moins déterministe qu'une règle ; le résultat dépend fortement des labels, du seuil et du modèle local."],
        ],
    ))

    content.append(heading("3.5 Branche Regex - formats structurés", 2))
    content.append(paragraph(
        "La branche Regex ne cherche pas à comprendre le sens du texte. Elle identifie des formats structurés connus et sensibles, avec des expressions régulières déterministes."
    ))
    content.append(table(
        ["Règle", "Type détecté", "Score"],
        [
            ["EMAIL_ADDRESS", "Adresse email", "0,95"],
            ["PHONE_NUMBER_FR", "Numéro de téléphone français", "0,90"],
            ["IBAN_FR", "IBAN français", "0,95"],
            ["FR_NIR", "Numéro NIR français", "0,95"],
        ],
    ))

    content.append(page_break())
    content.append(heading("4. Chapitre modèles ML utilisés"))
    content.append(heading("4.1 Principes de gouvernance des modèles", 2))
    for item in [
        "Les modèles sont prévus pour une exécution locale, sans appel externe pendant l'analyse.",
        "Le stockage local des modèles se fait via COMPLIANCE_NLP_MODEL_STORE, avec un cache COMPLIANCE_NLP_MODEL_CACHE.",
        "Les modèles ML ne remplacent pas le référentiel métier ; ils complètent la détection et remontent des suspicions supplémentaires.",
        "Les alertes ML doivent rester explicables par un label, un score et un extrait de preuve.",
    ]:
        content.append(bullet(item))

    content.append(heading("4.2 Modèle spaCy fr_core_news_md", 2))
    content.append(paragraph(
        "spaCy est utilisé comme moteur linguistique français. Le modèle fr_core_news_md permet de produire des tokens, lemmes et informations linguistiques utiles à la comparaison des formes de mots. "
        "Dans ce projet, spaCy sert principalement à reconnaître des variantes grammaticales et lexicales autour des termes du référentiel."
    ))
    content.append(table(
        ["Point", "Description"],
        [
            ["Rôle", "Analyse linguistique locale, lemmatisation et support aux synonymes contrôlés."],
            ["Chemin attendu", "E:\\Workspace\\modelStore\\fr_core_news_md, selon la configuration du notebook."],
            ["Dépendances", "spacy>=3.7.0 et spacy-lookups-data."],
            ["Données de configuration", "configs/spacy_synonyms.csv, rafraîchi depuis Mots_interdits.csv avec conservation des synonymes existants."],
            ["Apport", "Réduit les faux négatifs liés aux accords, pluriels et formes fléchies."],
            ["Risque", "Peut introduire des rapprochements trop larges si les synonymes sont mal maîtrisés."],
        ],
    ))

    content.append(heading("4.3 Modèle GLiNER gliner_multi-v2.1", 2))
    content.append(paragraph(
        "GLiNER est utilisé pour la reconnaissance d'entités nommées et de concepts à partir de labels configurables. "
        "Le modèle gliner_multi-v2.1 permet d'indiquer au moteur les catégories recherchées, par exemple une donnée de santé, une opinion politique ou une clause bénéficiaire imprécise."
    ))
    content.append(table(
        ["Point", "Description"],
        [
            ["Rôle", "Reconnaissance conceptuelle et entités configurables."],
            ["Modèle source", "urchade/gliner_multi-v2.1."],
            ["Chemin attendu", "E:\\Workspace\\modelStore\\gliner_multi-v2.1, selon la configuration du notebook."],
            ["Seuil", "0,50 dans le notebook 03e."],
            ["Dépendance", "gliner>=0.2.0."],
            ["Apport", "Détecte des idées formulées autrement que le mot exact du référentiel."],
            ["Risque", "Résultats probabilistes à contrôler ; calibrage nécessaire sur des cas métier réels."],
        ],
    ))

    content.append(heading("4.4 JeuxDeMots", 2))
    content.append(paragraph(
        "JeuxDeMots n'est pas un modèle de prédiction utilisé au moment de l'analyse. Il sert uniquement, de manière optionnelle, à enrichir le fichier de synonymes spaCy lors d'une phase de préparation. "
        "Le notebook de comparaison force allow_network=False afin de rester local et reproductible."
    ))

    content.append(page_break())
    content.append(heading("5. Spécification technique"))
    content.append(heading("5.1 Architecture technique", 2))
    content.append(image(technical_img, width_inches=6.9))

    content.append(heading("5.2 Modules applicatifs", 2))
    content.append(table(
        ["Module", "Responsabilité"],
        [
            ["src/compliance_nlp/pipeline.py", "Orchestration globale : extraction, sections, branches activées, agrégation et sérialisation."],
            ["src/compliance_nlp/config.py", "Chargement des CSV, construction des règles, whitelist, synonymes spaCy et enrichissement optionnel JeuxDeMots."],
            ["src/compliance_nlp/generic.py", "Détection déterministe par règles métier."],
            ["src/compliance_nlp/linguistic.py", "Détection linguistique spaCy."],
            ["src/compliance_nlp/gliner_detector.py", "Détection conceptuelle GLiNER."],
            ["src/compliance_nlp/regex_detector.py", "Détection par expressions régulières."],
            ["src/compliance_nlp/models.py", "Dataclasses Finding et DocumentAnalysis."],
            ["src/compliance_nlp/notebook.py", "Helpers pour DataFrame, records et synthèses notebook."],
            ["src/compliance_nlp/pdf.py", "Extraction texte PDF via pypdf."],
        ],
    ))

    content.append(heading("5.3 Pipeline technique", 2))
    for item in [
        "analyze_file lit un PDF, extrait le texte, charge les règles et appelle analyze_text.",
        "analyze_text construit une section document unique, exécute les branches activées et consolide les findings.",
        "analyze_directory applique le traitement à tous les PDF d'un dossier.",
        "save_results et load_results sérialisent les résultats JSON.",
        "Les métadonnées contiennent les compteurs par branche, les scores maximums et les erreurs éventuelles de chargement modèle.",
    ]:
        content.append(bullet(item))

    content.append(heading("5.4 Modèle de données de sortie", 2))
    content.append(table(
        ["Champ", "Signification"],
        [
            ["code", "Identifiant fonctionnel ou technique de l'alerte."],
            ["severity / alert_level", "Criticité et niveau d'alerte."],
            ["section", "Section analysée, actuellement document."],
            ["title / detail", "Libellé et détail de l'alerte."],
            ["evidence", "Extrait textuel utilisé comme preuve."],
            ["matched_term", "Terme ou extrait détecté."],
            ["score / branch_score", "Score de confiance global et score de branche."],
            ["generic_score / spacy_score / gliner_score / regex_score", "Score spécialisé par moteur."],
            ["detection_type", "Type de reconnaissance : exact, lemma, root, fuzzy, entity, regex."],
            ["detection_engine", "Branche source : generic, spacy, gliner, regex."],
            ["rule_id / rule_scope / regulatory_family", "Traçabilité vers la règle et la famille réglementaire."],
        ],
    ))

    content.append(heading("5.5 Notebooks et exploitation", 2))
    content.append(table(
        ["Notebook", "Rôle"],
        [
            ["01_lancer_traitement.ipynb", "Lancement du traitement PDF et génération des résultats."],
            ["02_analyser_resultats_scores.ipynb", "Analyse des alertes, scores et files de revue humaine."],
            ["03a_tester_branche_generic.ipynb", "Test isolé de la branche Generic."],
            ["03b_tester_branche_spacy.ipynb", "Test isolé de la branche spaCy."],
            ["03c_tester_branche_gliner.ipynb", "Test isolé de la branche GLiNER."],
            ["03d_tester_branche_presidio.ipynb", "Notebook expérimental autour d'une branche Presidio."],
            ["03e_tester_comparaison_branches.ipynb", "Comparaison centralisée des quatre branches generic, spacy, gliner et regex."],
        ],
    ))

    content.append(heading("6. Exigences non fonctionnelles", 1))
    for item in [
        "Traçabilité : chaque alerte doit conserver son moteur, sa règle, son score et sa preuve.",
        "Explicabilité : les règles métier doivent rester lisibles et modifiables dans les fichiers CSV.",
        "Localité : aucune dépendance réseau ne doit être nécessaire lors d'une analyse courante.",
        "Reproductibilité : les modèles ML et les cas de test doivent être versionnés ou stockés de manière stable.",
        "Extensibilité : une nouvelle branche doit pouvoir être ajoutée sans modifier le modèle de sortie principal.",
        "Sécurité : les résultats peuvent contenir des données personnelles et doivent être stockés dans un espace maîtrisé.",
    ]:
        content.append(bullet(item))

    content.append(heading("7. Stratégie de tests et recette", 1))
    for item in [
        "Tests unitaires sur la détection des mots interdits et le périmètre de section document.",
        "Tests de non-régression sur les cas configs/test_cases.csv.",
        "Comparaison des compteurs par branche via count_pivot_df dans le notebook 03e.",
        "Revue métier des faux positifs et faux négatifs avant généralisation.",
        "Calibrage spécifique des seuils GLiNER sur un corpus représentatif.",
    ]:
        content.append(bullet(item))

    content.append(heading("8. Limites connues et évolutions proposées", 1))
    content.append(table(
        ["Limite", "Impact", "Évolution proposée"],
        [
            ["Analyse en section document unique", "Pas de distinction fine entre zones métier du formulaire.", "Réintroduire des sections métier si le besoin PO le justifie."],
            ["Référentiel CSV simple", "Gouvernance manuelle des règles.", "Ajouter version, propriétaire, date de validation et statut de règle."],
            ["GLiNER probabiliste", "Variabilité des résultats selon labels et seuils.", "Mettre en place un jeu de calibration et des seuils par famille."],
            ["Regex limité aux formats codés", "Ne couvre pas toutes les données personnelles.", "Ajouter de nouveaux motifs validés par sécurité/conformité."],
            ["Synonymes spaCy à contrôler", "Risque d'élargissement excessif.", "Workflow de validation métier des synonymes proposés."],
        ],
    ))

    content.append(heading("9. Annexes", 1))
    content.append(heading("9.1 Labels GLiNER configurés", 2))
    content.append(paragraph(", ".join(GLINER_LABELS) + "."))
    content.append(heading("9.2 Expressions whitelist Article 9", 2))
    if WHITELIST_ROWS:
        content.append(table(
            ["Expression", "Raison"],
            [[row.get("expression", ""), row.get("reason", "")] for row in WHITELIST_ROWS],
        ))
    content.append(heading("9.3 Fichiers clés du projet", 2))
    for item in [
        "configs/Mots_interdits.csv",
        "configs/article9_whitelist.csv",
        "configs/spacy_synonyms.csv",
        "configs/test_cases.csv",
        "scripts/run_analysis.py",
        "scripts/generate_full_project_spec_docx.py",
        "src/compliance_nlp/",
        "notebooks/03e_tester_comparaison_branches.ipynb",
    ]:
        content.append(bullet(item))

    content.append(
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="900" w:right="800" w:bottom="900" w:left="800" w:header="708" w:footer="708" w:gutter="0"/>'
        "</w:sectPr>"
    )
    return content


def build_docx() -> None:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}" xmlns:wp="{WP_NS}" xmlns:a="{A_NS}" xmlns:pic="{PIC_NS}">'
        f"<w:body>{''.join(body_content())}</w:body></w:document>"
    )

    styles_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W_NS}">
<w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="21"/></w:rPr><w:pPr><w:spacing w:after="120"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="1F4E79"/><w:sz w:val="36"/></w:rPr><w:pPr><w:spacing w:after="260"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:rPr><w:b/><w:color w:val="1F4E79"/><w:sz w:val="30"/></w:rPr><w:pPr><w:spacing w:before="260" w:after="140"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:rPr><w:b/><w:color w:val="5B9BD5"/><w:sz w:val="25"/></w:rPr><w:pPr><w:spacing w:before="180" w:after="100"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:style>
<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:color="BFBFBF"/><w:left w:val="single" w:sz="4" w:color="BFBFBF"/><w:bottom w:val="single" w:sz="4" w:color="BFBFBF"/><w:right w:val="single" w:sz="4" w:color="BFBFBF"/><w:insideH w:val="single" w:sz="4" w:color="BFBFBF"/><w:insideV w:val="single" w:sz="4" w:color="BFBFBF"/></w:tblBorders></w:tblPr></w:style>
</w:styles>'''

    numbering_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="{W_NS}"><w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>'''

    doc_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>',
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>',
    ]
    for rel_id, target_name, _ in image_rels:
        doc_rels.append(
            f'<Relationship Id="{rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{target_name}"/>'
        )
    doc_rels.append("</Relationships>")

    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Default Extension="png" ContentType="image/png"/>',
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>',
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>',
        '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>',
        "</Types>",
    ]

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )

    with zipfile.ZipFile(DOCX_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "".join(content_types))
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/styles.xml", styles_xml)
        archive.writestr("word/numbering.xml", numbering_xml)
        archive.writestr("word/_rels/document.xml.rels", "".join(doc_rels))
        for _, target_name, source_path in image_rels:
            archive.write(source_path, f"word/media/{target_name}")


if __name__ == "__main__":
    build_docx()
    print(DOCX_PATH)
