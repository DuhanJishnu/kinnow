"""Markdown conversions to HTML, PDF, and plain text using PySide6's QTextDocument."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QGuiApplication, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from .registry import register

HTML_TEMPLATE = """<!DOCTYPE html>
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
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      line-height: 1.6;
      color: #24292f;
      background-color: #ffffff;
    }}
    @media (prefers-color-scheme: dark) {{
      body {{ color: #e6edf3; background-color: #0d1117; }}
      pre, code {{ background-color: #161b22; }}
      table tr {{ background-color: #0d1117; border-top-color: #30363d; }}
      table tr:nth-child(2n) {{ background-color: #161b22; }}
      table th, table td {{ border-color: #30363d; }}
      blockquote {{ border-left-color: #30363d; color: #8b949e; }}
    }}
    h1, h2, h3, h4 {{ margin-top: 24px; margin-bottom: 16px; font-weight: 600; line-height: 1.25; }}
    h1 {{ padding-bottom: 0.3em; font-size: 2em; border-bottom: 1px solid rgba(127,127,127,0.2); }}
    h2 {{ padding-bottom: 0.3em; font-size: 1.5em; border-bottom: 1px solid rgba(127,127,127,0.2); }}
    pre {{ padding: 16px; overflow: auto; border-radius: 6px; font-size: 88%; background-color: #f6f8fa; }}
    code {{ padding: 0.2em 0.4em; border-radius: 4px; font-size: 88%; background-color: rgba(175,184,193,0.2); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }}
    blockquote {{ padding: 0 1em; border-left: 0.25em solid #d0d7de; margin: 0; color: #57606a; }}
    table {{ border-spacing: 0; border-collapse: collapse; margin-top: 0; margin-bottom: 16px; width: 100%; }}
    table th, table td {{ padding: 6px 13px; border: 1px solid #d0d7de; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def _get_qapp():
    return QGuiApplication.instance() or QGuiApplication(sys.argv if hasattr(sys, "argv") else [])


@register(["md", "markdown"], "html")
def md_to_html(src: Path, dst: Path) -> None:
    _get_qapp()
    md_text = src.read_text(encoding="utf-8", errors="replace")
    doc = QTextDocument()
    doc.setMarkdown(md_text)
    body_html = doc.toHtml()

    # Extract body content from QTextDocument HTML
    start = body_html.find("<body")
    end = body_html.rfind("</body>")
    if start != -1 and end != -1:
        body_content = body_html[body_html.find(">", start) + 1 : end]
    else:
        body_content = body_html

    full_html = HTML_TEMPLATE.format(title=src.stem, body=body_content)
    dst.write_text(full_html, encoding="utf-8")


@register(["md", "markdown"], "pdf")
def md_to_pdf(src: Path, dst: Path) -> Path:
    _get_qapp()
    md_text = src.read_text(encoding="utf-8", errors="replace")
    doc = QTextDocument()
    doc.setMarkdown(md_text)

    writer = QPdfWriter(str(dst))
    writer.setPageSize(QPageSize.A4)
    layout = QPageLayout()
    layout.setPageSize(QPageSize(QPageSize.A4))
    layout.setMargins(QMarginsF(15, 15, 15, 15))
    writer.setPageLayout(layout)

    doc.print_(writer)
    return dst


@register(["md", "markdown"], "txt")
def md_to_txt(src: Path, dst: Path) -> None:
    _get_qapp()
    md_text = src.read_text(encoding="utf-8", errors="replace")
    doc = QTextDocument()
    doc.setMarkdown(md_text)
    dst.write_text(doc.toPlainText(), encoding="utf-8")
