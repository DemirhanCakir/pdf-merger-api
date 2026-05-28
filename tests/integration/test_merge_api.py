import io
import uuid

import pytest
from pypdf import PdfReader

from tests.helpers import make_pdf_bytes

pytestmark = pytest.mark.integration


def _upload(client, page_count: int) -> str:
    resp = client.post(
        "/api/v1/files",
        files={
            "file": (
                f"src-{page_count}.pdf",
                io.BytesIO(make_pdf_bytes(page_count)),
                "application/pdf",
            )
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_full_merge_flow_produces_downloadable_pdf(client) -> None:
    a = _upload(client, 2)
    b = _upload(client, 3)

    resp = client.post("/api/v1/merge", json={"file_ids": [a, b]})
    assert resp.status_code == 202
    job_id = resp.json()["id"]

    # TestClient runs BackgroundTasks synchronously after the response
    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["status"] == "completed", body
    assert body["output_s3_key"]
    assert body["download_url"]

    dl = client.get(f"/api/v1/jobs/{job_id}/download")
    assert dl.status_code == 200
    assert dl.headers["content-type"] == "application/pdf"

    merged = PdfReader(io.BytesIO(dl.content))
    assert len(merged.pages) == 5


def test_merge_rejects_unknown_file_id(client) -> None:
    a = _upload(client, 1)
    bogus = str(uuid.uuid4())

    resp = client.post("/api/v1/merge", json={"file_ids": [a, bogus]})
    assert resp.status_code == 404


def test_merge_requires_at_least_two_files(client) -> None:
    a = _upload(client, 1)
    resp = client.post("/api/v1/merge", json={"file_ids": [a]})
    assert resp.status_code == 422


def test_get_unknown_job_returns_404(client) -> None:
    resp = client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_download_pending_job_returns_409(client, db_session) -> None:
    """Create a job row directly without running the background task."""
    from src.models import JobStatus, MergeJob, PdfFile
    from tests.factories import PdfFileFactory

    f1: PdfFile = PdfFileFactory.build()
    f2: PdfFile = PdfFileFactory.build()
    db_session.add_all([f1, f2])
    db_session.commit()

    job = MergeJob(
        source_file_ids=[str(f1.id), str(f2.id)],
        status=JobStatus.pending,
    )
    db_session.add(job)
    db_session.commit()

    resp = client.get(f"/api/v1/jobs/{job.id}/download")
    assert resp.status_code == 409
