import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.db import get_session
from src.models import JobStatus, MergeJob, PdfFile
from src.schemas import MergeJobOut, MergeRequest
from src.services import pdf_merger, s3_client

router = APIRouter(prefix="/api/v1", tags=["merge"])


def _to_out(job: MergeJob) -> MergeJobOut:
    download_url = None
    if job.status == JobStatus.completed and job.output_s3_key:
        download_url = s3_client.presigned_url(job.output_s3_key)
    return MergeJobOut(
        id=job.id,
        status=job.status,
        source_file_ids=[uuid.UUID(str(x)) for x in job.source_file_ids],
        output_s3_key=job.output_s3_key,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
        download_url=download_url,
    )


@router.post("/merge", response_model=MergeJobOut, status_code=status.HTTP_202_ACCEPTED)
def create_merge_job(
    payload: MergeRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> MergeJobOut:
    file_ids = payload.file_ids
    found = session.query(PdfFile).filter(PdfFile.id.in_(file_ids)).count()
    if found != len(file_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more file_ids do not exist",
        )

    job = MergeJob(source_file_ids=[str(fid) for fid in file_ids])
    session.add(job)
    session.commit()
    session.refresh(job)

    background_tasks.add_task(pdf_merger.run_merge_job, job.id)
    return _to_out(job)


@router.get("/jobs/{job_id}", response_model=MergeJobOut)
def get_job(job_id: uuid.UUID, session: Session = Depends(get_session)) -> MergeJobOut:
    job = session.get(MergeJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _to_out(job)


@router.get("/jobs/{job_id}/download")
def download_job(job_id: uuid.UUID, session: Session = Depends(get_session)) -> StreamingResponse:
    job = session.get(MergeJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != JobStatus.completed or not job.output_s3_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not ready (status={job.status.value})",
        )

    data = s3_client.download_bytes(job.output_s3_key)
    headers = {"Content-Disposition": f'attachment; filename="merged-{job.id}.pdf"'}
    return StreamingResponse(
        iter([data]), media_type="application/pdf", headers=headers
    )
