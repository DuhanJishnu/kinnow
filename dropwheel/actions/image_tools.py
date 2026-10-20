"""Image quick tools: Compress and optimize."""
from __future__ import annotations

from pathlib import Path

from dropwheel.actions.registry import register_action
from dropwheel.utils import unique_path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def _is_all_images(paths: list[Path]) -> bool:
    return bool(paths) and all(p.suffix.lower() in IMAGE_EXTS for p in paths)


@register_action(
    id="compress_img",
    label="COMPRESS",
    title="Optimize & Compress Image",
    is_applicable=_is_all_images,
)
def compress_image(paths: list[Path]) -> Path:
    """Compress image with web-optimized settings."""
    from PIL import Image

    last_out = None
    for src in paths:
        ext = src.suffix.lower()
        dst = unique_path(src.with_name(f"{src.stem}_compressed{ext}"))
        with Image.open(src) as im:
            fmt = im.format or "JPEG"
            if fmt.upper() in ("JPEG", "JPG"):
                im.save(dst, "JPEG", optimize=True, quality=80)
            elif fmt.upper() == "PNG":
                im.save(dst, "PNG", optimize=True)
            elif fmt.upper() == "WEBP":
                im.save(dst, "WEBP", quality=80, method=6)
            else:
                im.save(dst, fmt, optimize=True)
        last_out = dst
    return last_out or paths[0]
