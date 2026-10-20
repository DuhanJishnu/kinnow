from pathlib import Path
import fitz
import pytest

from dropwheel.actions import load_all_actions
from dropwheel.actions.pdf_tools import compress_pdf, merge_pdfs, split_pdf
from dropwheel.actions.registry import applicable_actions, get_action
from dropwheel.utils import natural_sort_key


@pytest.fixture(autouse=True)
def init_actions():
    load_all_actions()


def test_natural_sort_key():
    filenames = ["doc10.pdf", "doc2.pdf", "doc1.pdf", "doc20.pdf", "doc3.pdf"]
    sorted_names = sorted(filenames, key=natural_sort_key)
    assert sorted_names == ["doc1.pdf", "doc2.pdf", "doc3.pdf", "doc10.pdf", "doc20.pdf"]


def test_compress_pdf(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page(width=300, height=300)
    page.insert_text((50, 50), "Hello world")
    doc.save(str(pdf_path))
    doc.close()

    out = compress_pdf([pdf_path])
    assert out.exists()
    assert out.name == "test_compressed.pdf"
    with fitz.open(out) as out_doc:
        assert out_doc.page_count == 1
        assert "Hello world" in out_doc[0].get_text()


def test_merge_pdfs_order(tmp_path):
    # Create 3 PDFs with specific markers
    p10 = tmp_path / "item10.pdf"
    p2 = tmp_path / "item2.pdf"
    p1 = tmp_path / "item1.pdf"

    for p, text in [(p1, "First Page"), (p2, "Second Page"), (p10, "Tenth Page")]:
        doc = fitz.open()
        page = doc.new_page(width=200, height=200)
        page.insert_text((20, 20), text)
        doc.save(str(p))
        doc.close()

    # Pass in scrambled order
    out = merge_pdfs([p10, p1, p2])
    assert out.exists()
    assert out.name == "item1_merged.pdf"

    with fitz.open(out) as merged:
        assert merged.page_count == 3
        # Check natural sorting order: item1, item2, item10
        assert "First Page" in merged[0].get_text()
        assert "Second Page" in merged[1].get_text()
        assert "Tenth Page" in merged[2].get_text()


def test_split_pdf(tmp_path):
    pdf_path = tmp_path / "multipage.pdf"
    doc = fitz.open()
    for i in range(1, 4):
        p = doc.new_page(width=200, height=200)
        p.insert_text((20, 20), f"Page {i}")
    doc.save(str(pdf_path))
    doc.close()

    out_folder = split_pdf([pdf_path])
    assert out_folder.is_dir()
    assert out_folder.name == "multipage_pages"
    assert (out_folder / "page_1.pdf").exists()
    assert (out_folder / "page_2.pdf").exists()
    assert (out_folder / "page_3.pdf").exists()

    with fitz.open(out_folder / "page_2.pdf") as single:
        assert single.page_count == 1
        assert "Page 2" in single[0].get_text()


def test_applicable_actions(tmp_path):
    # Single 1-page PDF
    p1 = tmp_path / "single.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(p1))
    doc.close()

    actions_single = applicable_actions([p1])
    action_ids = [a.id for a in actions_single]
    assert "compress_pdf" in action_ids
    assert "merge_pdf" not in action_ids   # Need >= 2 PDFs to merge
    assert "split_pdf" not in action_ids   # Only 1 page

    # Multiple PDFs
    p2 = tmp_path / "second.pdf"
    doc2 = fitz.open()
    doc2.new_page()
    doc2.save(str(p2))
    doc2.close()

    actions_multi = applicable_actions([p1, p2])
    multi_ids = [a.id for a in actions_multi]
    assert "merge_pdf" in multi_ids
    assert "compress_pdf" in multi_ids
