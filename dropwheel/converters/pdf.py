"""PDF conversions using PyMuPDF (imported as `fitz`)."""
from __future__ import annotations

from pathlib import Path

from .registry import register
from dropwheel.utils import unique_path


@register(["pdf"], "png")
def pdf_to_png(src: Path, dst: Path) -> Path:
    import fitz  # PyMuPDF

    with fitz.open(src) as doc:
        if doc.page_count == 1:
            doc[0].get_pixmap(dpi=150).save(str(dst))
            return dst
        # Multi-page: put one PNG per page in a folder next to the PDF.
        folder = unique_path(dst.with_suffix(""))
        folder.mkdir(parents=True, exist_ok=True)
        for i, page in enumerate(doc, start=1):
            page.get_pixmap(dpi=150).save(str(folder / f"page_{i}.png"))
        return folder


@register(["pdf"], "txt")
def pdf_to_txt(src: Path, dst: Path) -> None:
    import fitz

    with fitz.open(src) as doc:
        text = "\n\n".join(page.get_text() for page in doc)
    dst.write_text(text, encoding="utf-8")
