"""Archive quick tools: Zip and Extract."""
from __future__ import annotations

import os
from pathlib import Path
import tarfile
import zipfile

from dropwheel.actions.registry import register_action
from dropwheel.utils import unique_path

ARCHIVE_EXTS = {".zip", ".tar", ".gz", ".tgz", ".bz2"}


def _is_all_archives(paths: list[Path]) -> bool:
    return bool(paths) and all(p.suffix.lower() in ARCHIVE_EXTS for p in paths)


def _can_create_archive(paths: list[Path]) -> bool:
    # Offer ZIP if not already purely zip archives
    return bool(paths) and any(p.suffix.lower() not in ARCHIVE_EXTS for p in paths)


@register_action(
    id="create_zip",
    label="ZIP",
    title="Compress to ZIP Archive",
    is_applicable=_can_create_archive,
)
def create_zip_archive(paths: list[Path]) -> Path:
    """Compress the selected files and folders into a ZIP archive."""
    if not paths:
        raise ValueError("No files provided to zip")

    first = paths[0]
    if len(paths) == 1:
        dst = unique_path(first.with_name(f"{first.name}.zip" if first.is_dir() else f"{first.stem}.zip"))
    else:
        dst = unique_path(first.with_name(f"{first.stem}_archive.zip"))

    with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            p = p.resolve()
            if p.is_dir():
                for root, _, files in os.walk(p):
                    root_path = Path(root)
                    rel_dir = root_path.relative_to(p.parent)
                    for file in files:
                        file_path = root_path / file
                        arcname = str(rel_dir / file)
                        zf.write(file_path, arcname)
            else:
                zf.write(p, p.name)

    return dst


@register_action(
    id="extract_archive",
    label="EXTRACT",
    title="Extract Archive Contents",
    is_applicable=_is_all_archives,
)
def extract_archive(paths: list[Path]) -> Path:
    """Extract archives safely into dedicated folders."""
    last_folder = None
    for src in paths:
        dst_folder = unique_path(src.parent / f"{src.stem}_extracted")
        dst_folder.mkdir(parents=True, exist_ok=True)
        dest_resolved = dst_folder.resolve()

        ext = src.suffix.lower()
        if ext == ".zip":
            with zipfile.ZipFile(src, "r") as zf:
                for member in zf.infolist():
                    # Security: Prevent directory traversal (Zip Slip)
                    target = (dst_folder / member.filename).resolve()
                    if not str(target).startswith(str(dest_resolved)):
                        continue
                    zf.extract(member, dst_folder)
        elif ext in {".tar", ".gz", ".tgz", ".bz2"}:
            with tarfile.open(src, "r:*") as tf:
                for member in tf.getmembers():
                    target = (dst_folder / member.name).resolve()
                    if not str(target).startswith(str(dest_resolved)):
                        continue
                    tf.extract(member, dst_folder)

        last_folder = dst_folder

    return last_folder or paths[0]
