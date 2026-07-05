from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


OUT = Path("visuel_notebook_03e_branches_csv_windows.pptx")
EMU = 6350
SLIDE_W = 1920 * EMU
SLIDE_H = 1080 * EMU


def emu(value: float) -> int:
    return int(round(value * EMU))


class SlideBuilder:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self.shape_id = 1

    def _id(self) -> int:
        self.shape_id += 1
        return self.shape_id

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str,
        line: str | None = None,
        radius: bool = True,
        name: str = "Shape",
    ) -> None:
        sid = self._id()
        geom = "roundRect" if radius else "rect"
        ln = (
            f'<a:ln w="9525"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>'
            if line
            else '<a:ln><a:noFill/></a:ln>'
        )
        self.parts.append(
            f"""
            <p:sp>
              <p:nvSpPr><p:cNvPr id="{sid}" name="{escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
              <p:spPr>
                <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
                <a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>
                <a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>
                {ln}
              </p:spPr>
              <p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>
            </p:sp>
            """
        )

    def ellipse(self, x: float, y: float, w: float, h: float, fill: str, alpha: int = 45000) -> None:
        sid = self._id()
        self.parts.append(
            f"""
            <p:sp>
              <p:nvSpPr><p:cNvPr id="{sid}" name="Soft circle"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
              <p:spPr>
                <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
                <a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>
                <a:solidFill><a:srgbClr val="{fill}"><a:alpha val="{alpha}"/></a:srgbClr></a:solidFill>
                <a:ln><a:noFill/></a:ln>
              </p:spPr>
              <p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>
            </p:sp>
            """
        )

    def text(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        text: str,
        size: int = 18,
        color: str = "41546B",
        bold: bool = False,
        align: str = "l",
        name: str = "Text",
    ) -> None:
        sid = self._id()
        b = ' b="1"' if bold else ""
        paragraphs = []
        for line in text.split("\n"):
            paragraphs.append(
                f"""
                <a:p>
                  <a:pPr algn="{align}"/>
                  <a:r><a:rPr lang="fr-FR" sz="{size * 100}"{b}><a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>{escape(line)}</a:t></a:r>
                  <a:endParaRPr lang="fr-FR" sz="{size * 100}"/>
                </a:p>
                """
            )
        self.parts.append(
            f"""
            <p:sp>
              <p:nvSpPr><p:cNvPr id="{sid}" name="{escape(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
              <p:spPr>
                <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
                <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                <a:noFill/><a:ln><a:noFill/></a:ln>
              </p:spPr>
              <p:txBody><a:bodyPr wrap="square" inset="0" lIns="0" tIns="0" rIns="0" bIns="0"/><a:lstStyle/>{''.join(paragraphs)}</p:txBody>
            </p:sp>
            """
        )

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = "0078D4") -> None:
        sid = self._id()
        x, y = min(x1, x2), min(y1, y2)
        w, h = abs(x2 - x1), abs(y2 - y1)
        flip_h = ' flipH="1"' if x2 < x1 else ""
        flip_v = ' flipV="1"' if y2 < y1 else ""
        self.parts.append(
            f"""
            <p:cxnSp>
              <p:nvCxnSpPr><p:cNvPr id="{sid}" name="Connector"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>
              <p:spPr>
                <a:xfrm{flip_h}{flip_v}><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(max(w, 1))}" cy="{emu(max(h, 1))}"/></a:xfrm>
                <a:prstGeom prst="straightConnector1"><a:avLst/></a:prstGeom>
                <a:ln w="25400"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:tailEnd type="triangle"/></a:ln>
              </p:spPr>
            </p:cxnSp>
            """
        )

    def xml(self) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="F7FBFF"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      {''.join(self.parts)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
"""


def add_csv_card(s: SlideBuilder, y: float, title: str, body: str, note: str, color: str) -> None:
    s.rect(112, y, 410, 104, "FFFFFF", "D7E9FB")
    s.rect(136, y + 24, 46, 46, color, None)
    s.text(147, y + 39, 30, 20, "CSV", 14, "FFFFFF", True, "ctr")
    s.text(202, y + 26, 286, 28, title, 22, "101827", True)
    s.text(202, y + 59, 300, 24, body, 17, "41546B")
    s.text(202, y + 84, 300, 18, note, 14, "66788D")


def add_branch(s: SlideBuilder, y: float, num: str, title: str, detect: str, cover: str) -> None:
    s.rect(1198, y, 630, 142, "FFFFFF", "CFE6FF")
    s.rect(1224, y + 31, 76, 76, "E8F3FF", None)
    s.text(1237, y + 55, 45, 28, num, 22, "0078D4", True, "ctr")
    s.text(1326, y + 36, 170, 34, title, 28, "101827", True)
    s.text(1326, y + 83, 462, 24, detect, 18, "41546B")
    s.text(1326, y + 112, 462, 24, cover, 18, "41546B")


def build_slide() -> str:
    s = SlideBuilder()
    s.ellipse(16, -10, 380, 380, "DFF1FF", 58000)
    s.ellipse(1490, 670, 480, 480, "EAF3FF", 75000)

    s.rect(78, 184, 492, 752, "FFFFFF", "D7E9FB")
    s.rect(112, 218, 132, 42, "E8F3FF", None)
    s.text(142, 230, 90, 24, "CSV sources", 16, "0078D4", True)
    s.text(112, 288, 320, 38, "Inputs pris en compte", 28, "101827", True)

    add_csv_card(
        s,
        344,
        "Mots_interdits.csv",
        "Regles metier : categorie, terme interdit, justification.",
        "Alimente le referentiel de detection.",
        "0078D4",
    )
    add_csv_card(
        s,
        470,
        "spacy_synonyms.csv",
        "Dictionnaire de synonymes et variantes.",
        "Utilise et enrichi par la branche spacy.",
        "00A2ED",
    )
    add_csv_card(
        s,
        596,
        "whitelist.csv",
        "Expressions a exclure des alertes.",
        "Filtre les faux positifs apres detection.",
        "107C10",
    )
    add_csv_card(
        s,
        722,
        "test_cases.csv",
        "Cas de test pour mesurer les performances.",
        "Compare precision, scores et detections par branche.",
        "8764B8",
    )

    s.rect(708, 352, 322, 292, "0078D4", None)
    s.rect(744, 390, 250, 54, "2B88D8", None)
    s.rect(744, 466, 250, 54, "2B88D8", None)
    s.rect(744, 542, 250, 54, "2B88D8", None)
    s.text(770, 407, 210, 28, "JupyterHub notebook", 22, "FFFFFF", True)
    s.text(772, 483, 180, 24, "analyze_text()", 18, "FFFFFF")
    s.text(772, 559, 210, 24, "comparison_df / scores", 18, "FFFFFF")
    s.text(710, 684, 310, 34, "Comparaison centrale", 28, "101827", True, "ctr")
    s.text(678, 725, 390, 24, "Activation des branches et consolidation des resultats.", 18, "41546B", False, "ctr")

    s.line(572, 560, 700, 500)
    s.line(1032, 495, 1176, 245)
    s.line(1032, 505, 1176, 423)
    s.line(1032, 525, 1176, 651)
    s.line(1032, 535, 1176, 829)

    add_branch(
        s,
        174,
        "01",
        "generic",
        "Detecte : termes exacts, racines, fuzzy et synonymes configures.",
        "Couvre : regles metier explicables et alertes scorees.",
    )
    add_branch(
        s,
        352,
        "02",
        "spacy",
        "Detecte : lemmes, formes flechies, racines et synonymes enrichis.",
        "Enrichit : spacy_synonyms.csv depuis les termes metier.",
    )
    add_branch(
        s,
        580,
        "03",
        "gliner",
        "Detecte : entites par labels, meme sans mot cle exact.",
        "Couvre : signaux sensibles et notions de conformite/conseil.",
    )
    add_branch(
        s,
        758,
        "04",
        "regex",
        "Detecte : formats structures via motifs deterministes.",
        "Couvre : email, telephone FR, IBAN FR et NIR francais.",
    )

    s.rect(86, 966, 1742, 54, "FFFFFF", "D7E9FB")
    s.text(
        122,
        984,
        1640,
        24,
        "Sorties notebook : case_summary, alerts, whitelist_ignored, comparison, count_pivot, score_view et branch_errors en CSV.",
        18,
        "41546B",
    )
    return s.xml()


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""

PRESENTATION = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId2"/></p:sldMasterIdLst>
  <p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst>
  <p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}" type="wide"/>
  <p:notesSz cx="6858000" cy="9144000"/>
  <p:defaultTextStyle/>
</p:presentation>
"""

PRESENTATION_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>
</Relationships>
"""

SLIDE_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>
"""

MASTER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
  <p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>
</p:sldMaster>
"""

MASTER_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>
"""

LAYOUT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>
"""

LAYOUT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>
"""

THEME = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Windows clean">
  <a:themeElements>
    <a:clrScheme name="Office"><a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F2937"/></a:dk2><a:lt2><a:srgbClr val="F7FBFF"/></a:lt2><a:accent1><a:srgbClr val="0078D4"/></a:accent1><a:accent2><a:srgbClr val="8764B8"/></a:accent2><a:accent3><a:srgbClr val="107C10"/></a:accent3><a:accent4><a:srgbClr val="00A2ED"/></a:accent4><a:accent5><a:srgbClr val="5C2D91"/></a:accent5><a:accent6><a:srgbClr val="2B88D8"/></a:accent6><a:hlink><a:srgbClr val="0078D4"/></a:hlink><a:folHlink><a:srgbClr val="5C2D91"/></a:folHlink></a:clrScheme>
    <a:fontScheme name="Segoe"><a:majorFont><a:latin typeface="Segoe UI"/></a:majorFont><a:minorFont><a:latin typeface="Segoe UI"/></a:minorFont></a:fontScheme>
    <a:fmtScheme name="Clean"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
  </a:themeElements>
  <a:objectDefaults/><a:extraClrSchemeLst/>
</a:theme>
"""

CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Visuel branches NLP</dc:title><dc:creator>Codex</dc:creator>
</cp:coreProperties>
"""

APP = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex</Application><PresentationFormat>On-screen Show (16:9)</PresentationFormat><Slides>1</Slides>
</Properties>
"""


def main() -> None:
    with ZipFile(OUT, "w", ZIP_DEFLATED) as pptx:
        pptx.writestr("[Content_Types].xml", CONTENT_TYPES)
        pptx.writestr("_rels/.rels", ROOT_RELS)
        pptx.writestr("ppt/presentation.xml", PRESENTATION)
        pptx.writestr("ppt/_rels/presentation.xml.rels", PRESENTATION_RELS)
        pptx.writestr("ppt/slides/slide1.xml", build_slide())
        pptx.writestr("ppt/slides/_rels/slide1.xml.rels", SLIDE_RELS)
        pptx.writestr("ppt/slideMasters/slideMaster1.xml", MASTER)
        pptx.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", MASTER_RELS)
        pptx.writestr("ppt/slideLayouts/slideLayout1.xml", LAYOUT)
        pptx.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", LAYOUT_RELS)
        pptx.writestr("ppt/theme/theme1.xml", THEME)
        pptx.writestr("docProps/core.xml", CORE)
        pptx.writestr("docProps/app.xml", APP)
    print(OUT.resolve())


if __name__ == "__main__":
    main()
