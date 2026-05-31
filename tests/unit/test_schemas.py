import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models import JobStatus
from src.schemas import MergeJobOut, MergeRequest, PdfFileList, PdfFileOut


def test_merge_request_requires_at_least_two_file_ids() -> None:
    with pytest.raises(ValidationError):
        MergeRequest(file_ids=[uuid.uuid4()])


def test_merge_request_accepts_valid_payload() -> None:
    ids = [uuid.uuid4(), uuid.uuid4()]
    req = MergeRequest(file_ids=ids)
    assert req.file_ids == ids


def test_merge_request_rejects_more_than_max() -> None:
    ids = [uuid.uuid4() for _ in range(51)]
    with pytest.raises(ValidationError):
        MergeRequest(file_ids=ids)


def test_pdf_file_out_serializes_uuid_and_datetime() -> None:
    pid = uuid.uuid4()
    now = datetime.now(UTC)
    out = PdfFileOut(id=pid, filename="x.pdf", size_bytes=100, page_count=3, uploaded_at=now)
    dumped = out.model_dump(mode="json")
    assert dumped["id"] == str(pid)
    assert dumped["filename"] == "x.pdf"


def test_pdf_file_list_aggregates_items() -> None:
    items = [
        PdfFileOut(
            id=uuid.uuid4(),
            filename="a.pdf",
            size_bytes=1,
            page_count=1,
            uploaded_at=datetime.now(UTC),
        )
    ]
    lst = PdfFileList(items=items, total=1)
    assert lst.total == 1
    assert len(lst.items) == 1


def test_merge_job_out_carries_status_enum() -> None:
    out = MergeJobOut(
        id=uuid.uuid4(),
        status=JobStatus.completed,
        source_file_ids=[uuid.uuid4()],
        created_at=datetime.now(UTC),
    )
    assert out.status == JobStatus.completed
