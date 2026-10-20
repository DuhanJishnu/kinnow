"""Plain text and source code conversions to PDF and HTML."""
from __future__ import annotations

import html
import sys
from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QGuiApplication, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from .registry import register

TEXT_FORMATS = ["txt", "log", "ini", "cfg", "conf", "json", "csv", "tsv", "py", "sql"]

TEXT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{
      max-width: 900px;
      margin: 30px auto;
      padding: 0 20px;
      font-family: Consolas, "Courier New", monospace;
      font-size: 13px;
      line-height: 1.5;
      color: #24292f;
      background-color: #ffffff;
    }}
    @media (prefers-color-scheme: dark) {{
      body {{ color: #e6edf3; background-color: #0d1117; }}
      pre {{ background-color: #161b22 !important; border-color: #30363d !important; }}
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-all;
      background-color: #f6f8fa;
      border: 1px solid #d0d7de;
      padding: 16px;
      border-radius: 6px;
    }}
  </style>
</head>
<body>
  <h2>{title}</h2>
  <pre>{content}</pre>
</body>
</html>
"""


def _get_qapp():
    return QGuiApplication.instance() or QGuiApplication(sys.argv if hasattr(sys, "argv") else [])


@register(TEXT_FORMATS, "pdf")
def text_to_pdf(src: Path, dst: Path) -> None:
    """Render plain text / code to a neat printable PDF."""
    _get_qapp()
    raw = src.read_text(encoding="utf-8", errors="replace")
    escaped = html.escape(raw)

    doc = QTextDocument()
    # Format with clean styling for printable PDF
    doc.setHtml(
        f'<h2 style="font-family: sans-serif; font-size: 14pt; margin-bottom: 8px;">{html.escape(src.name)}</h2>'
        f'<pre style="font-family: Consolas, monospace; font-size: 9.5pt; line-height: 1.45; white-space: pre-wrap;">{escaped}</pre>'
    )

    writer = QPdfWriter(str(dst))
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setPageOrientation(QPageLayout.Portrait)
    writer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Millimeter)

    doc.print_(writer)


@register(TEXT_FORMATS, "html")
def text_to_html(src: Path, dst: Path) -> None:
    """Format plain text / code into a standalone HTML file."""
    raw = src.read_text(encoding="utf-8", errors="replace")
    full_html = TEXT_HTML_TEMPLATE.format(
        title=html.escape(src.name),
        content=html.escape(raw),
    )
    dst.write_text(full_html, encoding="utf-8")
