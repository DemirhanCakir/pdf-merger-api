import io

import pytest

from tests.helpers import make_pdf_bytes

pytestmark = pytest.mark.integration


def test_upload_pdf_persists_file_and_returns_metadata(client) -> None:
    pdf = make_pdf_bytes(3)

    resp = client.post(
        "/api/v1/files",
        files={"file": ("sample.pdf", io.BytesIO(pdf), "application/pdf")},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "sample.pdf"
    assert body["page_count"] == 3
    assert body["size_bytes"] == len(pdf)
    assert "id" in body


def test_upload_rejects_non_pdf_content_type(client) -> None:
    resp = client.post(
        "/api/v1/files",
        files={"file": ("hello.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 415


def test_upload_rejects_garbage_pdf_payload(client) -> None:
    resp = client.post(
        "/api/v1/files",
        files={"file": ("bad.pdf", io.BytesIO(b"not a pdf"), "application/pdf")},
    )
    assert resp.status_code == 400


def test_list_files_returns_uploaded_items(client) -> None:
    for n in (1, 2, 3):
        client.post(
            "/api/v1/files",
            files={"file": (f"f{n}.pdf", io.BytesIO(make_pdf_bytes(n)), "application/pdf")},
        )

    resp = client.get("/api/v1/files")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


def test_list_files_respects_limit_offset(client) -> None:
    for n in range(5):
        client.post(
            "/api/v1/files",
            files={"file": (f"x{n}.pdf", io.BytesIO(make_pdf_bytes(1)), "application/pdf")},
        )

    resp = client.get("/api/v1/files?limit=2&offset=1")
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
