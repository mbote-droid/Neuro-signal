"""Format a pandoc .docx for submission: Times New Roman 12 pt, double line
spacing, continuous line numbers, A4 with 2.5 cm margins and page numbers.

    python3 paper/jnm/docx_format.py paper/jnm/manuscript.docx
"""

# ruff: noqa: E501  (OOXML fragments are clearer unbroken)
from __future__ import annotations

import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

FONT = '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman" w:eastAsia="Times New Roman"/>'
SPACING = '<w:spacing w:line="480" w:lineRule="auto" w:before="0" w:after="0"/>'
SECT = (
    '<w:sectPr><w:footerReference w:type="default" r:id="rIdFooterPage"/>'
    '<w:pgSz w:w="11906" w:h="16838"/>'
    '<w:pgMar w:top="1418" w:right="1418" w:bottom="1418" w:left="1418" '
    'w:header="709" w:footer="709" w:gutter="0"/>'
    '<w:lnNumType w:countBy="1" w:restart="continuous"/></w:sectPr>'
)
FOOTER = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText>PAGE</w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>'
)


def styles(xml: str) -> str:
    # styles fall back to the default font and spacing; headings keep their sizes
    xml = re.sub(r"<w:rFonts [^>]*/>", "", xml)
    xml = re.sub(r"<w:spacing [^>]*/>", "", xml)
    xml = re.sub(r"<w:color [^>]*/>", "", xml)

    def size(m: re.Match) -> str:
        block = m.group(0)
        if re.search(r'w:styleId="(Heading\d|Title)"', block):
            return block
        return re.sub(r'<w:sz w:val="\d+"/>|<w:szCs w:val="\d+"/>', "", block)

    xml = re.sub(r"<w:style\b.*?</w:style>", size, xml, flags=re.S)
    # document defaults, set last: font, size and spacing for every style
    defaults = (
        "<w:docDefaults><w:rPrDefault><w:rPr>" + FONT + '<w:sz w:val="24"/>'
        '<w:szCs w:val="24"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr>'
        + SPACING
        + "</w:pPr></w:pPrDefault></w:docDefaults>"
    )
    xml = re.sub(r"<w:docDefaults>.*?</w:docDefaults>", defaults, xml, flags=re.S)
    # table cells (pandoc's Compact style) stay single-spaced
    compact = '<w:spacing w:line="240" w:lineRule="auto" w:before="0" w:after="0"/>'
    return re.sub(
        r'(<w:style [^>]*w:styleId="Compact"[^>]*>.*?)(</w:style>)',
        lambda m: (
            re.sub(r"<w:pPr>|<w:pPr/>", "<w:pPr>" + compact, m.group(1), count=1)
            + ("" if "<w:pPr" in m.group(1) else "<w:pPr>" + compact + "</w:pPr>")
            + m.group(2)
        ),
        xml,
        flags=re.S,
    )


def document(xml: str) -> str:
    xml = re.sub(r"<w:sectPr\b.*?</w:sectPr>", "", xml, flags=re.S)
    if 'xmlns:r="' not in xml[:2000]:
        xml = xml.replace(
            "<w:document ",
            '<w:document xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ',
            1,
        )
    return xml.replace("</w:body>", SECT + "</w:body>")


def main(path: Path) -> None:
    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(path) as z:
        z.extractall(tmp)
    (tmp / "word/styles.xml").write_text(
        styles((tmp / "word/styles.xml").read_text("utf-8")), "utf-8"
    )
    (tmp / "word/document.xml").write_text(
        document((tmp / "word/document.xml").read_text("utf-8")), "utf-8"
    )
    (tmp / "word/footerPage.xml").write_text(FOOTER, "utf-8")
    rels = tmp / "word/_rels/document.xml.rels"
    rels.write_text(
        rels.read_text("utf-8").replace(
            "</Relationships>",
            '<Relationship Id="rIdFooterPage" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footerPage.xml"/></Relationships>',
        ),
        "utf-8",
    )
    ct = tmp / "[Content_Types].xml"
    ct.write_text(
        ct.read_text("utf-8").replace(
            "</Types>",
            '<Override PartName="/word/footerPage.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>',
        ),
        "utf-8",
    )
    out = path.with_suffix(".tmp.docx")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(tmp.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(tmp).as_posix())
    shutil.rmtree(tmp)
    out.replace(path)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
