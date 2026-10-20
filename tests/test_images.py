import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from dropwheel.converters import images, registry  # noqa: E402,F401


def test_png_to_jpg_with_transparency(tmp_path):
    src = tmp_path / "pic.png"
    Image.new("RGBA", (20, 20), (255, 0, 0, 0)).save(src)
    out = registry.convert(src, "jpg")
    assert out.exists() and out.suffix == ".jpg"
    with Image.open(out) as im:
        assert im.size == (20, 20)
