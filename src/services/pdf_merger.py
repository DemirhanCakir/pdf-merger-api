import io
import logging
import uuid
from datetime import datetime, timezone

from pypdf import PdfReader, PdfWriter
from sqlalchemy.orm import Session

from src.db import get_engine
from src.models import JobStatus, MergeJob, PdfFile
from src.services import s3_client

logger = logging.getLogger(__name__)


class MergeError(Exception):
    pass


def count_pages(pdf_bytes: bytes) -> int:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return len(reader.pages)


def merge_pdf_bytes(pdf_blobs: list[bytes]) -> bytes:
    """Pure function: take a list of PDF byte strings, return one merged PDF as bytes."""
    if len(pdf_blobs) < 2:
        raise MergeError("Need at least 2 PDF files to merge")

    writer = PdfWriter()
    for blob in pdf_blobs:
        reader = PdfReader(io.BytesIO(blob))
        for page in reader.pages:
            writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def run_merge_job(job_id: uuid.UUID) -> None:
    """Background task: fetch source PDFs from S3, merge, upload result, update job row."""
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)
    session: Session = SessionLocal()
    try:
        job = session.get(MergeJob, job_id)
        if job is None:
            logger.error("Merge job %s not found", job_id)
            return

        job.status = JobStatus.processing
        session.commit()

        try:
            file_ids = [uuid.UUID(str(fid)) for fid in job.source_file_ids]
            files = session.query(PdfFile).filter(PdfFile.id.in_(file_ids)).all()
            by_id = {f.id: f for f in files}
            ordered = [by_id[fid] for fid in file_ids if fid in by_id]

            if len(ordered) != len(file_ids):
                raise MergeError("One or more source files not found")

            blobs = [s3_client.download_bytes(f.s3_key) for f in ordered]
            merged = merge_pdf_bytes(blobs)

            output_key = f"merged/{job.id}.pdf"
            s3_client.upload_fileobj(io.BytesIO(merged), output_key)

            job.status = JobStatus.completed
            job.output_s3_key = output_key
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
            logger.info("Merge job %s completed (%d pages)", job.id, count_pages(merged))
        except Exception as exc:
            logger.exception("Merge job %s failed", job.id)
            job.status = JobStatus.failed
            job.error_message = str(exc)[:1024]
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
    finally:
        session.close()
