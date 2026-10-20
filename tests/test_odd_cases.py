import logging
from pathlib import Path
import pytest
from PIL import Image

from dropwheel.app import setup_logging
from dropwheel.converters import images, media, pdf, registry
from dropwheel.converters.media import FFmpegNotFoundError


def test_no_extension_file(tmp_path):
    """File with no extension has no targets and raises UnsupportedConversion on convert."""
    f = tmp_path / "mystery_file"
    f.write_text("plain data")

    assert registry.targets_for(f) == []
    assert registry.common_targets([f]) == []

    with pytest.raises(registry.UnsupportedConversion) as exc_info:
        registry.convert(f, "png")
    assert "Cannot convert" in str(exc_info.value)


def test_several_files_dropped_at_once(tmp_path):
    """Several files dropped: common targets are computed, and multiple files can be converted."""
    p1 = tmp_path / "img1.png"
    p2 = tmp_path / "img2.jpg"
    p3 = tmp_path / "doc.txt"

    Image.new("RGB", (10, 10), (255, 0, 0)).save(p1)
    Image.new("RGB", (10, 10), (0, 255, 0)).save(p2)
    p3.write_text("hello")

    # Common targets between two image types
    common_img = registry.common_targets([p1, p2])
    assert "webp" in common_img
    assert "pdf" in common_img

    # Disparate file types share no common targets
    common_all = registry.common_targets([p1, p3])
    assert common_all == []

    # Batch conversion of multiple files
    out1 = registry.convert(p1, "webp")
    out2 = registry.convert(p2, "webp")
    assert out1.exists() and out1.suffix == ".webp"
    assert out2.exists() and out2.suffix == ".webp"


def test_name_already_exists(tmp_path):
    """Converting when target already exists produces non-destructive unique paths."""
    src = tmp_path / "photo.png"
    Image.new("RGB", (10, 10)).save(src)

    # First conversion creates photo.jpg
    out1 = registry.convert(src, "jpg")
    assert out1.name == "photo.jpg"

    # Second conversion creates photo (1).jpg instead of overwriting
    out2 = registry.convert(src, "jpg")
    assert out2.name == "photo (1).jpg"

    # Third conversion creates photo (2).jpg
    out3 = registry.convert(src, "jpg")
    assert out3.name == "photo (2).jpg"


def test_multipage_pdf_folder_already_exists(tmp_path, monkeypatch):
    """When a multi-page PDF output directory already exists, a unique folder name is used."""
    import fitz

    # Create a small 2-page PDF
    pdf_path = tmp_path / "doc.pdf"
    doc = fitz.open()
    doc.new_page(width=100, height=100)
    doc.new_page(width=100, height=100)
    doc.save(str(pdf_path))
    doc.close()

    # Pre-create the directory "doc" to cause collision
    existing_dir = tmp_path / "doc"
    existing_dir.mkdir()
    (existing_dir / "old.txt").write_text("do not overwrite")

    out_folder = registry.convert(pdf_path, "png")
    assert out_folder.is_dir()
    assert out_folder.name == "doc (1)"
    assert (out_folder / "page_1.png").exists()
    assert (out_folder / "page_2.png").exists()
    assert (existing_dir / "old.txt").read_text() == "do not overwrite"


def test_very_large_file(tmp_path):
    """Very large image conversions succeed without decompression errors or memory issues."""
    large_img = tmp_path / "huge.png"
    # Create a 4000x4000 image (16 megapixels)
    im = Image.new("RGB", (4000, 4000), color=(100, 150, 200))
    im.save(large_img)

    out = registry.convert(large_img, "jpg")
    assert out.exists()
    assert out.stat().st_size > 0
    with Image.open(out) as converted:
        assert converted.size == (4000, 4000)


def test_ffmpeg_missing_clear_message(monkeypatch, tmp_path):
    """When ffmpeg is missing, FFmpegNotFoundError is raised with clear instructions."""
    # Clear the lru_cache for find_ffmpeg
    media.find_ffmpeg.cache_clear()

    # Simulate missing ffmpeg in PATH and vendor
    monkeypatch.setattr(media.shutil, "which", lambda cmd: None)
    monkeypatch.setattr(media.Path, "exists", lambda self: False)
    monkeypatch.setattr(media.Path, "is_file", lambda self: False)

    with pytest.raises(FFmpegNotFoundError) as exc_info:
        media.find_ffmpeg()

    err = str(exc_info.value)
    assert "FFmpeg is missing" in err
    assert "winget install Gyan.FFmpeg" in err
    assert "vendor" in err

    # Reset cache after test
    media.find_ffmpeg.cache_clear()


def test_setup_logging_terminal_quiet(monkeypatch, tmp_path):
    """Logging config sets console to WARNING and writes INFO to a log file."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    log_file = setup_logging()

    root = logging.getLogger()
    assert root.level == logging.INFO

    # Find console handler
    console_handlers = [h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
    assert console_handlers
    assert console_handlers[0].level == logging.WARNING

    # Find file handler
    file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
    assert file_handlers
    assert file_handlers[0].level == logging.INFO
    assert log_file.exists()

    # Verify writing info writes to log file
    test_logger = logging.getLogger("test_logger")
    test_logger.info("This is an info message")
    for h in file_handlers:
        h.flush()
    assert "This is an info message" in log_file.read_text(encoding="utf-8")
