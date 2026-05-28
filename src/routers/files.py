import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.db import get_session
from src.models import PdfFile
from src.schemas import PdfFileList, PdfFileOut
from src.services import pdf_merger, s3_client

router = APIRouter(prefix="/api/v1/files", tags=["files"])


@router.post("", response_model=PdfFileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PdfFile:
    if file.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Only PDF files are accepted (got {file.content_type})",
        )

    contents = await file.read()
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max size {settings.max_upload_size_mb} MB",
        )

    try:
        page_count = pdf_merger.count_pages(contents)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse PDF: {exc}",
        ) from exc

    pdf_id = uuid.uuid4()
    key = f"uploads/{pdf_id}.pdf"
    s3_client.upload_fileobj(io.BytesIO(contents), key)

    row = PdfFile(
        id=pdf_id,
        filename=file.filename or "unnamed.pdf",
        s3_key=key,
        size_bytes=len(contents),
        page_count=page_count,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.get("", response_model=PdfFileList)
def list_files(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> PdfFileList:
    total = session.query(PdfFile).count()
    rows = (
        session.query(PdfFile)
        .order_by(PdfFile.uploaded_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return PdfFileList(items=[PdfFileOut.model_validate(r) for r in rows], total=total)
