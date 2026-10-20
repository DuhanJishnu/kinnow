"""Markdown quick tools for Tools Mode (Tab)."""
from __future__ import annotations

from pathlib import Path

from dropwheel.actions.registry import register_action
from dropwheel.converters.markdown import md_to_html, md_to_pdf
from dropwheel.utils import unique_path

MD_EXTS = {".md", ".markdown"}


def _is_all_md(paths: list[Path]) -> bool:
    return bool(paths) and all(p.suffix.lower() in MD_EXTS for p in paths)


@register_action(
    id="md_to_html_tool",
    label="HTML DOC",
    title="Render Markdown to HTML Document",
    is_applicable=_is_all_md,
)
def md_to_html_action(paths: list[Path]) -> Path:
    last_out = None
    for src in paths:
        dst = unique_path(src.with_suffix(".html"))
        md_to_html(src, dst)
        last_out = dst
    return last_out or paths[0]


@register_action(
    id="md_to_pdf_tool",
    label="PRINT PDF",
    title="Render Markdown to Formatted PDF",
    is_applicable=_is_all_md,
)
def md_to_pdf_action(paths: list[Path]) -> Path:
    last_out = None
    for src in paths:
        dst = unique_path(src.with_suffix(".pdf"))
        md_to_pdf(src, dst)
        last_out = dst
    return last_out or paths[0]
