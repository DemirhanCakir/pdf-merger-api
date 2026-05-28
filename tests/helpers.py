"""Test helpers for generating real PDF bytes."""

import io

from pypdf import PdfWriter


def make_pdf_bytes(page_count: int = 1) -> bytes:
    """Generate a valid PDF with the requested number of blank A4 pages."""
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
