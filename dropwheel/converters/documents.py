"""Word document (.docx) conversions to PDF, TXT, HTML, MD, PNG, and EPUB."""
from __future__ import annotations

import html
from pathlib import Path
import sys
import tempfile
import zipfile

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QGuiApplication, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from .registry import register

DOC_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{
      max-width: 820px;
      margin: 40px auto;
      padding: 0 24px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.6;
      color: #24292f;
      background-color: #ffffff;
    }}
    @media (prefers-color-scheme: dark) {{
      body {{ color: #e6edf3; background-color: #0d1117; }}
      table tr {{ background-color: #0d1117; border-top-color: #30363d; }}
      table th, table td {{ border-color: #30363d; }}
    }}
    h1, h2, h3, h4 {{ margin-top: 24px; margin-bottom: 16px; font-weight: 600; line-height: 1.25; }}
    table {{ border-spacing: 0; border-collapse: collapse; margin: 16px 0; width: 100%; }}
    table th, table td {{ padding: 6px 13px; border: 1px solid #d0d7de; }}
    p {{ margin-bottom: 1em; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def _get_qapp():
    return QGuiApplication.instance() or QGuiApplication(sys.argv if hasattr(sys, "argv") else [])


def _try_word_com_pdf(src: Path, dst: Path) -> bool:
    """Attempt conversion via Microsoft Word COM if available."""
    if sys.platform != "win32":
        return False
    try:
        import win32com.client  # type: ignore

        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        try:
            doc = word.Documents.Open(str(src.resolve()), ReadOnly=True)
            doc.ExportAsFixedFormat(str(dst.resolve()), 17)  # 17 = wdExportFormatPDF
            doc.Close(False)
            return True
        finally:
            word.Quit()
    except Exception:
        return False


def _standalone_docx_to_pdf(src: Path, dst: Path) -> None:
    """Pure Python standalone fallback: docx -> semantic HTML -> vector PDF."""
    import mammoth

    _get_qapp()
    with open(src, "rb") as f:
        res = mammoth.convert_to_html(f)
        body = res.value

    doc = QTextDocument()
    doc.setHtml(DOC_HTML_TEMPLATE.format(title=html.escape(src.stem), body=body))

    writer = QPdfWriter(str(dst))
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setPageOrientation(QPageLayout.Portrait)
    writer.setPageMargins(QMarginsF(20, 20, 20, 20), QPageLayout.Millimeter)
    doc.print_(writer)


@register(["docx", "doc"], "pdf")
def docx_to_pdf(src: Path, dst: Path) -> None:
    """Convert Word document to PDF (Word COM engine if available, or standalone vector engine)."""
    if _try_word_com_pdf(src, dst) and dst.exists():
        return
    _standalone_docx_to_pdf(src, dst)


@register(["docx", "doc"], "txt")
def docx_to_txt(src: Path, dst: Path) -> None:
    """Extract clean plaintext from Word document."""
    import docx

    doc = docx.Document(src)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    # Also extract text from tables
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                paragraphs.append(row_text)

    dst.write_text("\n\n".join(paragraphs), encoding="utf-8")


@register(["docx", "doc"], "html")
def docx_to_html(src: Path, dst: Path) -> None:
    """Convert Word document to semantic HTML with styling."""
    import mammoth

    with open(src, "rb") as f:
        res = mammoth.convert_to_html(f)
        body = res.value

    full_html = DOC_HTML_TEMPLATE.format(title=html.escape(src.stem), body=body)
    dst.write_text(full_html, encoding="utf-8")


@register(["docx", "doc"], "md")
def docx_to_md(src: Path, dst: Path) -> None:
    """Convert Word document to CommonMark Markdown."""
    import mammoth

    with open(src, "rb") as f:
        res = mammoth.convert_to_markdown(f)
        md_text = res.value

    dst.write_text(md_text, encoding="utf-8")


@register(["docx", "doc"], "png")
def docx_to_png(src: Path, dst: Path) -> None:
    """Render Word document to PNG image."""
    import pymupdf

    with tempfile.TemporaryDirectory() as td:
        tmp_pdf = Path(td) / "temp.pdf"
        docx_to_pdf(src, tmp_pdf)
        with pymupdf.open(tmp_pdf) as doc:
            if doc.page_count > 0:
                pix = doc[0].get_pixmap(dpi=150)
                pix.save(str(dst))


@register(["docx", "doc"], "epub")
def docx_to_epub(src: Path, dst: Path) -> None:
    """Package Word document into a standard EPUB book."""
    import mammoth

    with open(src, "rb") as f:
        res = mammoth.convert_to_html(f)
        body = res.value

    title = html.escape(src.stem)
    clean_body = body or f"<p>{title}</p>"

    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookID" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{title}</dc:title>
    <dc:language>en</dc:language>
    <dc:identifier id="BookID">urn:uuid:kinnow-{src.stem}</dc:identifier>
  </metadata>
  <manifest>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="chapter1"/>
  </spine>
</package>"""

    toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:kinnow-{src.stem}"/>
  </head>
  <docTitle><text>{title}</text></docTitle>
  <navMap>
    <navPoint id="navpoint-1" playOrder="1">
      <navLabel><text>{title}</text></navLabel>
      <content src="chapter1.xhtml"/>
    </navPoint>
  </navMap>
</ncx>"""

    chapter_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{title}</title>
  <style type="text/css">
    body {{ font-family: serif; line-height: 1.5; padding: 5%; }}
    h1, h2, h3 {{ font-family: sans-serif; }}
  </style>
</head>
<body>
{clean_body}
</body>
</html>"""

    with zipfile.ZipFile(dst, "w") as zf:
        # EPUB spec requires mimetype to be first and uncompressed
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container_xml, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/content.opf", content_opf, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/toc.ncx", toc_ncx, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/chapter1.xhtml", chapter_xhtml, compress_type=zipfile.ZIP_DEFLATED)
