"""Image quick tools: Compress, Strip EXIF, Resize 50%, and Grayscale."""
from __future__ import annotations

from pathlib import Path

from dropwheel.actions.registry import register_action
from dropwheel.utils import unique_path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}


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
    from PIL import Image, ImageOps

    last_out = None
    for src in paths:
        ext = src.suffix.lower()
        dst = unique_path(src.with_name(f"{src.stem}_compressed{ext}"))
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            fmt = im.format or ("PNG" if ext == ".png" else "JPEG")
            if fmt.upper() in ("JPEG", "JPG"):
                if im.mode in ("RGBA", "LA", "P"):
                    im = im.convert("RGB")
                im.save(dst, "JPEG", optimize=True, quality=80)
            elif fmt.upper() == "PNG":
                im.save(dst, "PNG", optimize=True)
            elif fmt.upper() == "WEBP":
                im.save(dst, "WEBP", quality=80, method=6)
            else:
                im.save(dst, fmt, optimize=True)
        last_out = dst
    return last_out or paths[0]


@register_action(
    id="strip_exif",
    label="STRIP EXIF",
    title="Remove EXIF & Privacy Metadata",
    is_applicable=_is_all_images,
)
def strip_exif(paths: list[Path]) -> Path:
    """Strip EXIF, GPS location, camera details, and device metadata."""
    from PIL import Image, ImageOps

    last_out = None
    for src in paths:
        ext = src.suffix.lower()
        dst = unique_path(src.with_name(f"{src.stem}_clean{ext}"))
        with Image.open(src) as im:
            # Physically orient pixels according to EXIF orientation before dropping the tag
            oriented = ImageOps.exif_transpose(im)
            fmt = im.format or ("PNG" if ext == ".png" else "JPEG")

            # Save without copying any EXIF, IPTC, or GPS tags
            if fmt.upper() in ("JPEG", "JPG"):
                if oriented.mode in ("RGBA", "LA", "P"):
                    oriented = oriented.convert("RGB")
                oriented.save(dst, "JPEG", quality=92)
            elif fmt.upper() == "PNG":
                oriented.save(dst, "PNG", optimize=True)
            elif fmt.upper() == "WEBP":
                oriented.save(dst, "WEBP", quality=90)
            else:
                oriented.save(dst, fmt)
        last_out = dst
    return last_out or paths[0]


@register_action(
    id="resize_half",
    label="RESIZE 50%",
    title="Resize Image to 50% (Half Size)",
    is_applicable=_is_all_images,
)
def resize_half(paths: list[Path]) -> Path:
    """Scale down image to 50% width and height using high quality Lanczos resampling."""
    from PIL import Image, ImageOps

    resample_filter = getattr(Image.Resampling, "LANCZOS", Image.LANCZOS)
    last_out = None
    for src in paths:
        ext = src.suffix.lower()
        dst = unique_path(src.with_name(f"{src.stem}_50pct{ext}"))
        with Image.open(src) as im:
            oriented = ImageOps.exif_transpose(im)
            new_w = max(1, oriented.width // 2)
            new_h = max(1, oriented.height // 2)
            resized = oriented.resize((new_w, new_h), resample=resample_filter)

            fmt = im.format or ("PNG" if ext == ".png" else "JPEG")
            if fmt.upper() in ("JPEG", "JPG") and resized.mode in ("RGBA", "LA", "P"):
                resized = resized.convert("RGB")
            resized.save(dst, fmt)
        last_out = dst
    return last_out or paths[0]


@register_action(
    id="grayscale_img",
    label="GRAYSCALE",
    title="Convert to Grayscale (B&W)",
    is_applicable=_is_all_images,
)
def grayscale_image(paths: list[Path]) -> Path:
    """Convert image to Black & White / Grayscale."""
    from PIL import Image, ImageOps

    last_out = None
    for src in paths:
        ext = src.suffix.lower()
        dst = unique_path(src.with_name(f"{src.stem}_bw{ext}"))
        with Image.open(src) as im:
            oriented = ImageOps.exif_transpose(im)
            if oriented.mode in ("RGBA", "LA") and ext == ".png":
                bw = oriented.convert("LA")
            else:
                bw = oriented.convert("L")

            fmt = im.format or ("PNG" if ext == ".png" else "JPEG")
            bw.save(dst, fmt)
        last_out = dst
    return last_out or paths[0]

