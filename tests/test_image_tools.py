from pathlib import Path
from PIL import Image
import pytest

from dropwheel.actions import load_all_actions
from dropwheel.actions.image_tools import (
    compress_image,
    grayscale_image,
    resize_half,
    strip_exif,
)
from dropwheel.actions.registry import applicable_actions


@pytest.fixture(autouse=True)
def init_actions():
    load_all_actions()


def test_strip_exif(tmp_path: Path):
    src = tmp_path / "photo_with_exif.jpg"
    im = Image.new("RGB", (60, 60), color="blue")
    exif = im.getexif()
    # Tag 0x010E is ImageDescription
    exif[0x010E] = "Kinnow Test Metadata"
    im.save(src, "JPEG", exif=exif)

    # Verify input has EXIF
    with Image.open(src) as in_im:
        assert in_im.getexif().get(0x010E) == "Kinnow Test Metadata"

    out = strip_exif([src])
    assert out.exists()
    assert out.name == "photo_with_exif_clean.jpg"

    # Verify output has NO exif tag
    with Image.open(out) as out_im:
        out_exif = out_im.getexif()
        assert out_exif.get(0x010E) is None


def test_resize_half(tmp_path: Path):
    src = tmp_path / "big_photo.png"
    Image.new("RGB", (120, 80), color="green").save(src, "PNG")

    out = resize_half([src])
    assert out.exists()
    assert out.name == "big_photo_50pct.png"

    with Image.open(out) as out_im:
        assert out_im.size == (60, 40)


def test_grayscale_image_rgb(tmp_path: Path):
    src = tmp_path / "color.jpg"
    Image.new("RGB", (50, 50), color="red").save(src, "JPEG")

    out = grayscale_image([src])
    assert out.exists()
    assert out.name == "color_bw.jpg"

    with Image.open(out) as out_im:
        assert out_im.mode == "L"


def test_grayscale_image_png_transparency(tmp_path: Path):
    src = tmp_path / "transparent.png"
    Image.new("RGBA", (50, 50), color=(255, 0, 0, 128)).save(src, "PNG")

    out = grayscale_image([src])
    assert out.exists()
    assert out.name == "transparent_bw.png"

    with Image.open(out) as out_im:
        assert out_im.mode == "LA"


def test_compress_image(tmp_path: Path):
    src = tmp_path / "uncompressed.png"
    Image.new("RGBA", (100, 100), color=(10, 20, 30, 255)).save(src, "PNG")

    out = compress_image([src])
    assert out.exists()
    assert out.name == "uncompressed_compressed.png"
    with Image.open(out) as out_im:
        assert out_im.size == (100, 100)


def test_image_tools_applicable(tmp_path: Path):
    src = tmp_path / "sample.jpg"
    Image.new("RGB", (30, 30), color="white").save(src, "JPEG")

    actions = applicable_actions([src])
    action_ids = [a.id for a in actions]

    assert "compress_img" in action_ids
    assert "strip_exif" in action_ids
    assert "resize_half" in action_ids
    assert "grayscale_img" in action_ids
