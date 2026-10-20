"""PDF productivity tools: Compress, Merge, and Split."""
from __future__ import annotations

from pathlib import Path

from dropwheel.actions.registry import register_action
from dropwheel.utils import natural_sort_key, unique_path


def _is_all_pdf(paths: list[Path]) -> bool:
    return bool(paths) and all(p.suffix.lower() == ".pdf" for p in paths)


def _can_merge_pdf(paths: list[Path]) -> bool:
    return len(paths) >= 2 and _is_all_pdf(paths)


def _can_split_pdf(paths: list[Path]) -> bool:
    if len(paths) != 1 or paths[0].suffix.lower() != ".pdf":
        return False
    try:
        import fitz
        with fitz.open(paths[0]) as doc:
            return doc.page_count > 1
    except Exception:
        return False


@register_action(
    id="compress_pdf",
    label="COMPRESS",
    title="Compress PDF File Size",
    is_applicable=_is_all_pdf,
)
def compress_pdf(paths: list[Path]) -> Path:
    """Compress PDF streams and remove redundant objects."""
    import fitz

    last_out = None
    for src in paths:
        dst = unique_path(src.with_name(f"{src.stem}_compressed.pdf"))
        with fitz.open(src) as doc:
            # garbage=4: compact xref table, remove all unused objects
            # deflate=True: recompress uncompressed streams
            # clean=True: clean and sanitize page content streams
            doc.save(dst, garbage=4, deflate=True, clean=True)
        last_out = dst
    return last_out or paths[0]


@register_action(
    id="merge_pdf",
    label="MERGE",
    title="Merge PDFs in Order",
    is_applicable=_can_merge_pdf,
)
def merge_pdfs(paths: list[Path]) -> Path:
    """Merge 2 or more PDFs in natural alphanumeric order."""
    import fitz

    sorted_paths = sorted(paths, key=natural_sort_key)
    first = sorted_paths[0]
    dst = unique_path(first.with_name(f"{first.stem}_merged.pdf"))

    merged = fitz.open()
    for p in sorted_paths:
        with fitz.open(p) as doc:
            merged.insert_pdf(doc)

    merged.save(dst, garbage=3, deflate=True)
    merged.close()
    return dst


@register_action(
    id="split_pdf",
    label="SPLIT",
    title="Split PDF Pages into Folder",
    is_applicable=_can_split_pdf,
)
def split_pdf(paths: list[Path]) -> Path:
    """Split multi-page PDF into individual single-page PDFs."""
    import fitz

    src = paths[0]
    folder = unique_path(src.with_name(f"{src.stem}_pages"))
    folder.mkdir(parents=True, exist_ok=True)

    with fitz.open(src) as doc:
        for i, page in enumerate(doc, start=1):
            single = fitz.open()
            single.insert_pdf(doc, from_page=i - 1, to_page=i - 1)
            single.save(folder / f"page_{i}.pdf", deflate=True)
            single.close()

    return folder
