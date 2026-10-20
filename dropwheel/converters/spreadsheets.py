"""Spreadsheet (.xlsx, .xls) conversions to CSV, TSV, PDF, and ODS."""
from __future__ import annotations

import csv
import html
from pathlib import Path
import sys
import zipfile

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QGuiApplication, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from .registry import register

SHEET_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 11px;
      margin: 20px;
      color: #24292f;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin-top: 12px;
    }}
    th, td {{
      border: 1px solid #d0d7de;
      padding: 6px 10px;
      text-align: left;
    }}
    th {{
      background-color: #f6f8fa;
      font-weight: 600;
    }}
    tr:nth-child(even) {{
      background-color: #fcfcfc;
    }}
  </style>
</head>
<body>
  <h2>{title}</h2>
  {table}
</body>
</html>
"""


def _get_qapp():
    return QGuiApplication.instance() or QGuiApplication(sys.argv if hasattr(sys, "argv") else [])


@register(["xlsx", "xls"], "csv")
def sheet_to_csv(src: Path, dst: Path) -> None:
    """Export active spreadsheet to Comma-Separated Values (CSV)."""
    import openpyxl

    wb = openpyxl.load_workbook(src, data_only=True)
    sheet = wb.active
    with open(dst, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for row in sheet.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                writer.writerow([str(cell) if cell is not None else "" for cell in row])


@register(["xlsx", "xls"], "tsv")
def sheet_to_tsv(src: Path, dst: Path) -> None:
    """Export active spreadsheet to Tab-Separated Values (TSV)."""
    import openpyxl

    wb = openpyxl.load_workbook(src, data_only=True)
    sheet = wb.active
    with open(dst, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter="\t")
        for row in sheet.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                writer.writerow([str(cell) if cell is not None else "" for cell in row])


@register(["xlsx", "xls"], "pdf")
def sheet_to_pdf(src: Path, dst: Path) -> None:
    """Render spreadsheet table to a landscape PDF."""
    import openpyxl

    _get_qapp()
    wb = openpyxl.load_workbook(src, data_only=True)
    sheet = wb.active

    rows_html = []
    is_first = True
    for row in sheet.iter_rows(values_only=True):
        if not any(cell is not None for cell in row):
            continue
        cells_html = []
        tag = "th" if is_first else "td"
        for cell in row:
            val = html.escape(str(cell)) if cell is not None else ""
            cells_html.append(f"<{tag}>{val}</{tag}>")
        rows_html.append(f"<tr>{''.join(cells_html)}</tr>")
        is_first = False

    table_content = f"<table>{''.join(rows_html)}</table>" if rows_html else "<p>Empty sheet</p>"
    full_html = SHEET_HTML_TEMPLATE.format(title=html.escape(src.stem), table=table_content)

    doc = QTextDocument()
    doc.setHtml(full_html)

    writer = QPdfWriter(str(dst))
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setPageOrientation(QPageLayout.Landscape)
    writer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Millimeter)
    doc.print_(writer)


@register(["xlsx", "xls"], "ods")
def sheet_to_ods(src: Path, dst: Path) -> None:
    """Package spreadsheet as OpenDocument Spreadsheet (.ods)."""
    import openpyxl

    wb = openpyxl.load_workbook(src, data_only=True)
    sheet = wb.active

    rows_xml = []
    for row in sheet.iter_rows(values_only=True):
        cells_xml = []
        for cell in row:
            val = html.escape(str(cell)) if cell is not None else ""
            cells_xml.append(
                f'<table:table-cell office:value-type="string"><text:p>{val}</text:p></table:table-cell>'
            )
        rows_xml.append(f"<table:table-row>{''.join(cells_xml)}</table:table-row>")

    content_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0">
  <office:body>
    <office:spreadsheet>
      <table:table table:name="{html.escape(sheet.title)}">
        {''.join(rows_xml)}
      </table:table>
    </office:spreadsheet>
  </office:body>
</office:document-content>"""

    manifest_xml = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">
  <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>
  <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
</manifest:manifest>"""

    with zipfile.ZipFile(dst, "w") as zf:
        zf.writestr(
            "mimetype", "application/vnd.oasis.opendocument.spreadsheet", compress_type=zipfile.ZIP_STORED
        )
        zf.writestr("META-INF/manifest.xml", manifest_xml, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("content.xml", content_xml, compress_type=zipfile.ZIP_DEFLATED)
