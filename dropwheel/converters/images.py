"""Image conversions using Pillow."""
from __future__ import annotations

from pathlib import Path

from .registry import register

IMAGE_IN = ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif"]
IMAGE_OUT = {  # target ext -> Pillow format name
    "png": "PNG",
    "jpg": "JPEG",
    "webp": "WEBP",
    "bmp": "BMP",
    "gif": "GIF",
    "pdf": "PDF",
}
NEEDS_RGB = {"JPEG", "BMP", "PDF"}  # formats that cannot store transparency


def _flatten_alpha(im):
    """Paste a transparent image onto white so JPG/PDF output isn't black."""
    from PIL import Image

    rgba = im.convert("RGBA")
    background = Image.new("RGB", rgba.size, (255, 255, 255))
    background.paste(rgba, mask=rgba.split()[3])
    return background


def _make_converter(fmt: str):
    def convert(src: Path, dst: Path) -> None:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None  # allow large images without DecompressionBombError

        with Image.open(src) as im:
            if fmt in NEEDS_RGB:
                im = _flatten_alpha(im) if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
            im.save(dst, fmt)

    return convert


for _ext, _fmt in IMAGE_OUT.items():
    register(IMAGE_IN, _ext)(_make_converter(_fmt))
