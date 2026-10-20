"""Presentation (.pptx, .ppt) conversions to PDF, PNG, and JPG."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile

from .registry import register
from dropwheel.utils import unique_path


def _try_ppt_com(src: Path, dst: Path, fmt_code: int) -> bool:
    """Attempt export via Microsoft PowerPoint COM if available.

    fmt_code: 2 = PDF (ppFixedFormatTypePDF), 17 = PNG (ppSaveAsPNG), 18 = JPG (ppSaveAsJPG)
    """
    if sys.platform != "win32":
        return False
    try:
        import win32com.client  # type: ignore

        ppt = win32com.client.DispatchEx("PowerPoint.Application")
        try:
            pres = ppt.Presentations.Open(str(src.resolve()), WithWindow=False)
            if fmt_code == 2:
                pres.ExportAsFixedFormat(str(dst.resolve()), 2)
            else:
                pres.SaveAs(str(dst.resolve()), fmt_code)
            pres.Close()
            return True
        finally:
            ppt.Quit()
    except Exception:
        return False


def _standalone_pptx_to_pdf(src: Path, dst: Path) -> None:
    """Pure Python standalone fallback: extract slide text & images to PDF using PyMuPDF."""
    import pptx
    import pymupdf

    prs = pptx.Presentation(src)
    pdf_doc = pymupdf.open()
    w = prs.slide_width.pt
    h = prs.slide_height.pt

    for slide in prs.slides:
        page = pdf_doc.new_page(width=w, height=h)
        y = 50
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        page.insert_text((50, y), text, fontsize=16)
                        y += 28
            elif shape.shape_type == 13:  # Picture
                try:
                    img_bytes = shape.image.blob
                    rect = pymupdf.Rect(
                        shape.left.pt,
                        shape.top.pt,
                        (shape.left + shape.width).pt,
                        (shape.top + shape.height).pt,
                    )
                    page.insert_image(rect, stream=img_bytes)
                except Exception:
                    pass

    if pdf_doc.page_count == 0:
        pdf_doc.new_page(width=w, height=h)

    pdf_doc.save(str(dst))
    pdf_doc.close()


@register(["pptx", "ppt"], "pdf")
def pptx_to_pdf(src: Path, dst: Path) -> None:
    """Convert PowerPoint presentation to PDF."""
    if _try_ppt_com(src, dst, 2) and dst.exists():
        return
    _standalone_pptx_to_pdf(src, dst)


@register(["pptx", "ppt"], "png")
def pptx_to_png(src: Path, dst: Path) -> Path:
    """Export PowerPoint presentation slides to PNG image(s)."""
    import pymupdf

    with tempfile.TemporaryDirectory() as td:
        tmp_pdf = Path(td) / "temp.pdf"
        pptx_to_pdf(src, tmp_pdf)
        with pymupdf.open(tmp_pdf) as doc:
            if doc.page_count <= 1:
                if doc.page_count == 1:
                    doc[0].get_pixmap(dpi=150).save(str(dst))
                return dst

            folder = unique_path(dst.with_suffix(""))
            folder.mkdir(parents=True, exist_ok=True)
            for i, page in enumerate(doc, start=1):
                page.get_pixmap(dpi=150).save(str(folder / f"slide_{i}.png"))
            return folder


@register(["pptx", "ppt"], "jpg")
def pptx_to_jpg(src: Path, dst: Path) -> Path:
    """Export PowerPoint presentation slides to JPG image(s)."""
    import pymupdf

    with tempfile.TemporaryDirectory() as td:
        tmp_pdf = Path(td) / "temp.pdf"
        pptx_to_pdf(src, tmp_pdf)
        with pymupdf.open(tmp_pdf) as doc:
            if doc.page_count <= 1:
                if doc.page_count == 1:
                    doc[0].get_pixmap(dpi=150).save(str(dst))
                return dst

            folder = unique_path(dst.with_suffix(""))
            folder.mkdir(parents=True, exist_ok=True)
            for i, page in enumerate(doc, start=1):
                page.get_pixmap(dpi=150).save(str(folder / f"slide_{i}.jpg"))
            return folder
