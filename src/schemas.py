import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models import JobStatus


class PdfFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    size_bytes: int
    page_count: int
    uploaded_at: datetime


class PdfFileList(BaseModel):
    items: list[PdfFileOut]
    total: int


class MergeRequest(BaseModel):
    file_ids: list[uuid.UUID] = Field(..., min_length=2, max_length=50)


class MergeJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: JobStatus
    source_file_ids: list[uuid.UUID]
    output_s3_key: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    download_url: str | None = None


class HealthOut(BaseModel):
    status: str
    database: str
    s3: str


class ErrorOut(BaseModel):
    detail: str
