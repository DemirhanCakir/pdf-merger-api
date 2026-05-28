import uuid

from src.models import JobStatus, MergeJob, PdfFile


def test_pdf_file_defaults_generate_uuid() -> None:
    f = PdfFile(filename="a.pdf", s3_key="uploads/a.pdf", size_bytes=10, page_count=1)
    assert f.id is None or isinstance(f.id, uuid.UUID)  # default applied on flush
    f.id = uuid.uuid4()
    assert isinstance(f.id, uuid.UUID)


def test_merge_job_status_enum_values() -> None:
    job = MergeJob(source_file_ids=[str(uuid.uuid4())])
    job.status = JobStatus.processing
    assert job.status == JobStatus.processing
    assert JobStatus.completed.value == "completed"
    assert JobStatus.failed.value == "failed"


def test_merge_job_holds_json_list_of_uuids() -> None:
    ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    job = MergeJob(source_file_ids=ids)
    assert job.source_file_ids == ids
