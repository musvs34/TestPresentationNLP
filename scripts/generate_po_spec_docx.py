from __future__ import annotations

import html
import zipfile
from pathlib import Path
from textwrap import wrap

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image


OUT_DIR = Path("outputs/specifications")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCX_PATH = OUT_DIR / "specification_detection_conformite_product_owner.docx"

COLORS = {
    "blue": "#D9EAF7",
    "green": "#DFF1E3",
    "yellow": "#FFF2CC",
    "orange": "#FCE4D6",
    "purple": "#EADCF8",
    "gray": "#EDEDED",
    "result": "#E2F0D9",
    "model": "#F4CCCC",
}


def draw_box(ax, xy, text, width=2.6, height=0.75, color="#EDEDED", fontsize=9):
    x, y = xy
    box = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.04,rounding_size=0.06",
        linewidth=1.2,
        edgecolor="#4A4A4A",
        facecolor=color,
    )
    ax.add_patch(box)
    ax.text(
        x + width / 2,
        y + height / 2,
        "\n".join(wrap(text, 25)),
        ha="center",
        va="center",
        fontsize=fontsize,
        color="#222222",
    )
    return (x, y, width, height)


def arrow_lr(ax, start_box, end_box):
    sx = start_box[0] + start_box[2]
    sy = start_box[1] + start_box[3] / 2
    ex = end_box[0]
    ey = end_box[1] + end_box[3] / 2
    ax.add_patch(FancyArrowPatch((sx, sy), (ex, ey), arrowstyle="-|>", mutation_scale=12, linewidth=1.1))


def arrow_down(ax, start_box, end_box):
    sx = start_box[0] + start_box[2] / 2
    sy = start_box[1]
    ex = end_box[0] + end_box[2] / 2
    ey = end_box[1] + end_box[3]
    ax.add_patch(FancyArrowPatch((sx, sy), (ex, ey), arrowstyle="-|>", mutation_scale=12, linewidth=1.1))


def save_functional_architecture(path: Path):
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis("off")
    ax.set_title("Architecture fonctionnelle cible", fontsize=15, weight="bold", pad=14)

    source = draw_box(ax, (0.5, 3.05), "Document ou texte de test", color=COLORS["blue"])
    load = draw_box(ax, (3.35, 3.05), "Extraction / chargement du texte", color=COLORS["gray"])
    sections = draw_box(ax, (6.15, 3.05), "Découpage en sections métier", color=COLORS["gray"])
    arrow_lr(ax, source, load)
    arrow_lr(ax, load, sections)

    branch_specs = [
        ("Generic\nRègles métier", 5.65, COLORS["green"]),
        ("spaCy\nLinguistique", 4.25, COLORS["yellow"]),
        ("GLiNER\nEntités / concepts", 2.85, COLORS["purple"]),
        ("Regex\nFormats structurés", 1.45, COLORS["orange"]),
    ]
    branches = [draw_box(ax, (9.25, y), label, color=color) for label, y, color in branch_specs]
    for branch in branches:
        arrow_lr(ax, sections, branch)

    result = draw_box(
        ax,
        (4.65, 0.25),
        "Alertes comparables\nScores par branche\nTableaux PO",
        width=3.7,
        height=0.95,
        color=COLORS["result"],
    )
    for branch in branches:
        sx = branch[0] + branch[2] / 2
        sy = branch[1]
        ex = result[0] + result[2] / 2
        ey = result[1] + result[3]
        ax.add_patch(FancyArrowPatch((sx, sy), (ex, ey), arrowstyle="-|>", mutation_scale=10, linewidth=1))

    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_technical_architecture(path: Path):
    fig, ax = plt.subplots(figsize=(11.2, 6.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis("off")
    ax.set_title("Architecture technique", fontsize=15, weight="bold", pad=14)

    cfg = draw_box(ax, (0.5, 5.45), "configs/*.csv\nRègles, sections, cas, synonymes", width=2.9, color=COLORS["blue"])
    text = draw_box(ax, (0.5, 3.7), "PDF / textes\nNotebooks", width=2.9, color=COLORS["blue"])
    pipe = draw_box(ax, (4.45, 4.55), "pipeline.py\nOrchestration", width=2.85, height=0.95, color="#DDEBF7")
    arrow_lr(ax, cfg, pipe)
    arrow_lr(ax, text, pipe)

    engines = [
        draw_box(ax, (8.45, 5.75), "generic.py", color=COLORS["green"]),
        draw_box(ax, (8.45, 4.55), "linguistic.py\nspaCy md", color=COLORS["yellow"]),
        draw_box(ax, (8.45, 3.35), "gliner_detector.py", color=COLORS["purple"]),
        draw_box(ax, (8.45, 2.15), "regex_detector.py", color=COLORS["orange"]),
    ]
    for engine in engines:
        arrow_lr(ax, pipe, engine)

    model_store = draw_box(
        ax,
        (4.25, 2.15),
        "modelStore\nfr_core_news_md\ngliner_multi-v2.1",
        width=3.15,
        height=1.05,
        color=COLORS["model"],
    )
    cache = draw_box(ax, (4.25, 0.9), "ModelCache\ncache modèles local", width=3.15, color=COLORS["model"])
    arrow_down(ax, pipe, model_store)
    arrow_down(ax, model_store, cache)

    result = draw_box(
        ax,
        (8.05, 0.65),
        "DocumentAnalysis\nFindings + metadata + scores",
        width=3.45,
        height=0.95,
        color=COLORS["result"],
    )
    for engine in engines:
        sx = engine[0] + engine[2] / 2
        sy = engine[1]
        ex = result[0] + result[2] / 2
        ey = result[1] + result[3]
        ax.add_patch(FancyArrowPatch((sx, sy), (ex, ey), arrowstyle="-|>", mutation_scale=10, linewidth=1))

    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_branch_specificity(path: Path):
    fig, ax = plt.subplots(figsize=(11, 5.8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.4)
    ax.axis("off")
    ax.set_title("Différences de reconnaissance par branche", fontsize=15, weight="bold", pad=14)

    src = draw_box(ax, (0.55, 2.8), "Texte à analyser", width=2.3, color=COLORS["blue"])
    branches = [
        draw_box(ax, (3.65, 5.1), "Generic\nMots exacts\nSynonymes CSV métier\nFuzzy simple", width=3.15, height=1.05, color=COLORS["green"], fontsize=8.5),
        draw_box(ax, (3.65, 3.55), "spaCy\nLemmes\nRacines\nSynonymes contrôlés", width=3.15, height=1.05, color=COLORS["yellow"], fontsize=8.5),
        draw_box(ax, (3.65, 2.0), "GLiNER\nLabels configurables\nEntités et concepts\nScore modèle", width=3.15, height=1.05, color=COLORS["purple"], fontsize=8.5),
        draw_box(ax, (3.65, 0.45), "Regex\nEmail\nTéléphone\nIBAN / NIR", width=3.15, height=1.05, color=COLORS["orange"], fontsize=8.5),
    ]
    for branch in branches:
        arrow_lr(ax, src, branch)

    result = draw_box(ax, (8.4, 2.45), "Résultats comparables\npar moteur et par score", width=3.2, height=1.1, color=COLORS["result"])
    for branch in branches:
        arrow_lr(ax, branch, result)

    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


functional_img = OUT_DIR / "architecture_fonctionnelle.png"
technical_img = OUT_DIR / "architecture_technique.png"
branch_img = OUT_DIR / "specificites_branches.png"
save_functional_architecture(functional_img)
save_technical_architecture(technical_img)
save_branch_specificity(branch_img)


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"

image_rels: list[tuple[str, str, Path]] = []
image_counter = 1


def esc(value) -> str:
    return html.escape(str(value), quote=False)


def paragraph(text="", style=None, bold=False, italic=False, center=False):
    parts = []
    if style or center:
        parts.append("<w:pPr>")
        if style:
            parts.append(f'<w:pStyle w:val="{style}"/>')
        if center:
            parts.append('<w:jc w:val="center"/>')
        parts.append("</w:pPr>")
    rpr = ""
    if bold or italic:
        rpr = "<w:rPr>" + ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "") + "</w:rPr>"
    return f'<w:p>{"".join(parts)}<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>'


def bullet(text):
    return (
        '<w:p><w:pPr><w:pStyle w:val="ListBullet"/>'
        '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>'
        f"<w:r><w:t>{esc(text)}</w:t></w:r></w:p>"
    )


def table(headers, rows):
    xml = ['<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="0" w:type="auto"/></w:tblPr>']
    for ridx, row in enumerate([headers] + rows):
        xml.append("<w:tr>")
        for cell in row:
            shade = '<w:shd w:fill="D9EAF7"/>' if ridx == 0 else ""
            xml.append(f"<w:tc><w:tcPr>{shade}</w:tcPr>{paragraph(cell, bold=(ridx == 0))}</w:tc>")
        xml.append("</w:tr>")
    xml.append("</w:tbl>")
    return "".join(xml)


def doc_image(path: Path, width_inches=6.6):
    global image_counter
    rel_id = f"rIdImg{image_counter}"
    name = f"image{image_counter}.png"
    image_counter += 1
    image_rels.append((rel_id, name, path))
    with Image.open(path) as im:
        width_px, height_px = im.size
    cx = int(width_inches * 914400)
    cy = int(cx * height_px / width_px)
    return f'''
<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:drawing>
<wp:inline distT="0" distB="0" distL="0" distR="0">
<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{image_counter}" name="{esc(path.stem)}"/>
<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
<pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="{esc(path.name)}"/><pic:cNvPicPr/></pic:nvPicPr>
<pic:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
</pic:pic></a:graphicData></a:graphic>
</wp:inline></w:drawing></w:r></w:p>
'''


body: list[str] = []
body.append(paragraph("Spécification - Détection conformité NLP", style="Title"))
body.append(paragraph("Document de synthèse pour Product Owner - 22 juin 2026", italic=True))
body.append(paragraph("Résumé exécutif", style="Heading1"))
body.append(paragraph("Le dispositif analyse des textes ou documents d’adhésion afin de détecter des alertes de conformité. Il compare quatre stratégies complémentaires : règles déterministes, analyse linguistique spaCy, reconnaissance d’entités GLiNER et expressions régulières pour données structurées."))
body.append(paragraph("Les résultats sont consolidés sous forme de Findings avec moteur, règle, section, terme détecté, score et métadonnées de branche."))

body.append(paragraph("1. Spécification Fonctionnelle", style="Heading1"))
body.append(paragraph("Objectif", style="Heading2"))
body.append(paragraph("Détecter automatiquement des alertes de conformité dans des documents ou textes de test, pour faciliter la revue métier et la comparaison des approches de reconnaissance."))
body.append(paragraph("Périmètre fonctionnel", style="Heading2"))
for item in [
    "Analyser un document complet ou des cas de test textuels.",
    "Découper le texte en sections métier lorsque le document suit la structure attendue.",
    "Activer ou désactiver chaque branche de détection depuis les notebooks.",
    "Comparer les scores et les résultats par branche.",
    "Centraliser les cas de test dans configs/test_cases.csv.",
    "Conserver les modèles localement dans D:\\Workspaces\\modelStore et le cache dans D:\\Workspaces\\ModelCache.",
]:
    body.append(bullet(item))

body.append(paragraph("Branches fonctionnelles", style="Heading2"))
body.append(table(
    ["Branche", "Rôle fonctionnel", "Exemples de détection"],
    [
        ["generic", "Contrôles déterministes à partir du référentiel métier CSV.", "sans risque, garantie, mes proches, diabétique"],
        ["spacy", "Contrôles linguistiques enrichis par lemmatisation et synonymes contrôlés.", "garantis, insuline, formes fléchies"],
        ["gliner", "Reconnaissance d’entités et de concepts à partir de labels configurables.", "maladie, opinion politique, donnée biométrique"],
        ["regex", "Détection déterministe de formats structurés.", "email, téléphone, IBAN, NIR"],
    ],
))
body.append(paragraph("Architecture fonctionnelle", style="Heading2"))
body.append(doc_image(functional_img))
body.append(paragraph("Critères d’acceptation fonctionnels", style="Heading2"))
for item in [
    "Chaque alerte indique le moteur, la règle ou catégorie, le terme détecté, le score et la section.",
    "Les branches sont comparables sur les mêmes cas de test.",
    "Les modèles ne sont pas téléchargés à chaque exécution.",
    "Le Product Owner peut identifier les faux positifs, les faux négatifs et les écarts entre branches.",
]:
    body.append(bullet(item))

body.append(paragraph("2. Spécification Technique", style="Heading1"))
body.append(paragraph("Composants principaux", style="Heading2"))
body.append(table(
    ["Composant", "Responsabilité"],
    [
        ["pipeline.py", "Orchestration des branches, agrégation des résultats et métadonnées."],
        ["generic.py", "Application des règles métier déterministes."],
        ["linguistic.py", "Branche spaCy avec fr_core_news_md et synonymes contrôlés."],
        ["gliner_detector.py", "Branche GLiNER avec modèle local et labels configurables."],
        ["regex_detector.py", "Branche regex pour données structurées."],
        ["configs/test_cases.csv", "Cas de test centralisés."],
        ["configs/spacy_synonyms.csv", "Synonymes proposés pour spaCy uniquement."],
        ["03e_tester_comparaison_branches.ipynb", "Notebook global de comparaison des quatre branches."],
    ],
))
body.append(paragraph("Architecture technique", style="Heading2"))
body.append(doc_image(technical_img))

body.append(paragraph("3. Spécificités des Branches", style="Heading1"))
body.append(paragraph("Vue comparative", style="Heading2"))
body.append(doc_image(branch_img))
body.append(table(
    ["Branche", "Type de reconnaissance", "Force principale", "Limite principale"],
    [
        ["generic", "Règles textuelles exactes, synonymes CSV métier, fuzzy simple.", "Très explicable et stable.", "Peu de compréhension du sens."],
        ["spacy", "Lemmes, racines, variantes grammaticales, synonymes contrôlés séparés.", "Meilleure couverture linguistique.", "Dépend du modèle et du référentiel de synonymes."],
        ["gliner", "Entités et concepts via labels configurables.", "Capacité sémantique plus large.", "Moins déterministe, sensible aux labels et seuils."],
        ["regex", "Expressions régulières sur formats structurés.", "Très fiable sur formats connus.", "Ne comprend pas le langage naturel."],
    ],
))

body.append(paragraph("Branche Generic", style="Heading2"))
body.append(paragraph("La branche generic est le moteur de référence déterministe. Elle lit les termes, synonymes métier, seuils et catégories depuis configs/generic_detection_rules.csv. Elle applique des recherches exactes, des rapprochements de racines simples et du fuzzy matching. Elle est recommandée comme base robuste et auditée."))
body.append(paragraph("Branche spaCy", style="Heading2"))
body.append(paragraph("La branche spaCy utilise le modèle local fr_core_news_md. Elle n’utilise plus les synonymes du CSV métier principal. Elle part des termes interdits puis enrichit la reconnaissance via configs/spacy_synonyms.csv. Cette séparation permet de comparer l’effet de l’enrichissement linguistique sans modifier le référentiel métier principal."))
body.append(paragraph("Branche GLiNER", style="Heading2"))
body.append(paragraph("La branche GLiNER détecte des entités ou concepts via des labels configurables. Elle permet de repérer des notions plus larges comme maladie, opinion politique ou donnée biométrique. Le résultat dépend du modèle local, du seuil et du libellé des labels."))
body.append(paragraph("Branche Regex", style="Heading2"))
body.append(paragraph("La branche regex détecte des données personnelles structurées sans modèle : adresse email, téléphone français, IBAN français et NIR français. Elle est rapide, déterministe et utile pour des formats normalisés."))

body.append(paragraph("4. Recommandation de Lecture pour le PO", style="Heading1"))
for item in [
    "Utiliser le notebook 03e pour comparer les branches sur les mêmes cas.",
    "Analyser les écarts entre generic et spaCy pour mesurer l’apport linguistique.",
    "Analyser GLiNER séparément pour les concepts sensibles non strictement couverts par les règles.",
    "Utiliser regex comme contrôle spécialisé sur les données structurées.",
]:
    body.append(bullet(item))

body.append('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1000" w:right="850" w:bottom="1000" w:left="850" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>')

document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}" xmlns:wp="{WP_NS}" xmlns:a="{A_NS}" xmlns:pic="{PIC_NS}"><w:body>{''.join(body)}</w:body></w:document>
'''

styles_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W_NS}">
<w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="22"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="34"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:rPr><w:b/><w:color w:val="1F4E79"/><w:sz w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:rPr><w:b/><w:color w:val="5B9BD5"/><w:sz w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:style>
<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4"/><w:left w:val="single" w:sz="4"/><w:bottom w:val="single" w:sz="4"/><w:right w:val="single" w:sz="4"/><w:insideH w:val="single" w:sz="4"/><w:insideV w:val="single" w:sz="4"/></w:tblBorders></w:tblPr></w:style>
</w:styles>
'''

numbering_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="{W_NS}"><w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>
'''

rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
rels.append('<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
rels.append('<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>')
for rel_id, name, _ in image_rels:
    rels.append(f'<Relationship Id="{rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{name}"/>')
rels.append("</Relationships>")

content_types = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">']
content_types.append('<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>')
content_types.append('<Default Extension="xml" ContentType="application/xml"/>')
content_types.append('<Default Extension="png" ContentType="image/png"/>')
content_types.append('<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>')
content_types.append('<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>')
content_types.append('<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>')
content_types.append("</Types>")

root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>
'''

with zipfile.ZipFile(DOCX_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("[Content_Types].xml", "".join(content_types))
    zf.writestr("_rels/.rels", root_rels)
    zf.writestr("word/document.xml", document_xml)
    zf.writestr("word/styles.xml", styles_xml)
    zf.writestr("word/numbering.xml", numbering_xml)
    zf.writestr("word/_rels/document.xml.rels", "".join(rels))
    for _, name, path in image_rels:
        zf.write(path, f"word/media/{name}")

print(DOCX_PATH.resolve())
