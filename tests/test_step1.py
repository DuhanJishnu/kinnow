from pathlib import Path
import zipfile
import pymupdf
import pytest

from dropwheel.actions import load_all_actions
from dropwheel.actions.archive_tools import create_zip_archive, extract_archive
from dropwheel.actions.file_tools import view_file_properties
from dropwheel.actions.registry import applicable_actions
from dropwheel.converters import load_all, registry


@pytest.fixture(autouse=True)
def init_all():
    load_all()
    load_all_actions()


def test_text_to_pdf(tmp_path: Path):
    src = tmp_path / "notes.txt"
    src.write_text("Line 1: Hello Kinnow\nLine 2: Testing text to PDF conversion.", encoding="utf-8")

    out = registry.convert(src, "pdf")
    assert out.exists()
    assert out.suffix == ".pdf"

    with pymupdf.open(out) as doc:
        assert doc.page_count >= 1
        text = doc[0].get_text()
        assert "Hello Kinnow" in text


def test_text_to_html(tmp_path: Path):
    src = tmp_path / "log.txt"
    src.write_text("INFO: System running smoothly.\n<tag>Special characters</tag>", encoding="utf-8")

    out = registry.convert(src, "html")
    assert out.exists()
    assert out.suffix == ".html"
    content = out.read_text(encoding="utf-8")
    assert "&lt;tag&gt;Special characters&lt;/tag&gt;" in content


def test_create_zip_single_file(tmp_path: Path):
    f1 = tmp_path / "document.pdf"
    f1.write_text("dummy pdf content")

    out_zip = create_zip_archive([f1])
    assert out_zip.exists()
    assert out_zip.name == "document.zip"

    with zipfile.ZipFile(out_zip, "r") as zf:
        namelist = zf.namelist()
        assert "document.pdf" in namelist


def test_create_zip_multiple_files(tmp_path: Path):
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f1.write_text("first")
    f2.write_text("second")

    out_zip = create_zip_archive([f1, f2])
    assert out_zip.exists()
    assert out_zip.name == "file1_archive.zip"

    with zipfile.ZipFile(out_zip, "r") as zf:
        namelist = zf.namelist()
        assert "file1.txt" in namelist
        assert "file2.txt" in namelist


def test_extract_archive_zip(tmp_path: Path):
    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("hello.txt", "Hello from inside zip")
        zf.writestr("subfolder/data.csv", "1,2,3")

    out_folder = extract_archive([zip_path])
    assert out_folder.is_dir()
    assert out_folder.name == "bundle_extracted"
    assert (out_folder / "hello.txt").exists()
    assert (out_folder / "hello.txt").read_text() == "Hello from inside zip"
    assert (out_folder / "subfolder" / "data.csv").exists()


def test_file_properties_action(tmp_path: Path):
    f = tmp_path / "sample.txt"
    f.write_text("sample")
    res = view_file_properties([f])
    assert res is None


def test_archive_actions_applicable(tmp_path: Path):
    txt_file = tmp_path / "item.txt"
    txt_file.write_text("content")

    actions = applicable_actions([txt_file])
    action_ids = [a.id for a in actions]
    assert "create_zip" in action_ids
    assert "file_properties" in action_ids

    # On an archive, EXTRACT should be applicable
    z = tmp_path / "archive.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("test.txt", "hi")

    actions_zip = applicable_actions([z])
    zip_action_ids = [a.id for a in actions_zip]
    assert "extract_archive" in zip_action_ids
    assert "file_properties" in zip_action_ids
