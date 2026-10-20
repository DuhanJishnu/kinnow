from pathlib import Path
import fitz
import pytest

from dropwheel.converters import load_all
from dropwheel.converters import registry
from dropwheel.converters.markdown import md_to_html, md_to_pdf, md_to_txt


@pytest.fixture(autouse=True)
def init_converters():
    load_all()


def test_markdown_targets():
    p = Path("README.md")
    targets = registry.targets_for(p)
    assert "html" in targets
    assert "pdf" in targets
    assert "txt" in targets


def test_md_to_html(tmp_path):
    src = tmp_path / "notes.md"
    src.write_text("# Project Notes\n\nThis is **bold** and *italic*.\n\n```python\nprint(1)\n```\n", encoding="utf-8")
    dst = tmp_path / "notes.html"

    md_to_html(src, dst)
    assert dst.exists()
    content = dst.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Project Notes" in content
    assert "print(1)" in content


def test_md_to_pdf(tmp_path):
    src = tmp_path / "doc.md"
    src.write_text("# Title Page\n\nSome important text content.", encoding="utf-8")
    dst = tmp_path / "doc.pdf"

    md_to_pdf(src, dst)
    assert dst.exists()
    with fitz.open(dst) as doc:
        assert doc.page_count >= 1
        assert "Title Page" in doc[0].get_text()


def test_md_to_txt(tmp_path):
    src = tmp_path / "plain.md"
    src.write_text("# Heading\n\n- Bullet 1\n- Bullet 2\n", encoding="utf-8")
    dst = tmp_path / "plain.txt"

    md_to_txt(src, dst)
    assert dst.exists()
    text = dst.read_text(encoding="utf-8")
    assert "Heading" in text
    assert "Bullet 1" in text
