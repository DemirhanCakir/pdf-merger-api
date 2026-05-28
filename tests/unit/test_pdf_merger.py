import io

import pytest
from pypdf import PdfReader

from src.services.pdf_merger import MergeError, count_pages, merge_pdf_bytes
from tests.helpers import make_pdf_bytes


def test_count_pages_returns_actual_page_count() -> None:
    assert count_pages(make_pdf_bytes(1)) == 1
    assert count_pages(make_pdf_bytes(5)) == 5
    assert count_pages(make_pdf_bytes(17)) == 17


def test_merge_two_single_page_pdfs_produces_two_page_pdf() -> None:
    a = make_pdf_bytes(1)
    b = make_pdf_bytes(1)

    merged = merge_pdf_bytes([a, b])

    reader = PdfReader(io.BytesIO(merged))
    assert len(reader.pages) == 2


def test_merge_preserves_page_count_across_all_inputs() -> None:
    blobs = [make_pdf_bytes(p) for p in (2, 3, 4)]

    merged = merge_pdf_bytes(blobs)

    assert count_pages(merged) == 2 + 3 + 4


def test_merge_rejects_single_input() -> None:
    with pytest.raises(MergeError):
        merge_pdf_bytes([make_pdf_bytes(1)])


def test_merge_rejects_empty_input() -> None:
    with pytest.raises(MergeError):
        merge_pdf_bytes([])


def test_count_pages_raises_on_garbage_bytes() -> None:
    with pytest.raises(Exception):
        count_pages(b"this is not a pdf")
