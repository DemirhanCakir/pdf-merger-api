"""Factory Boy models for test data."""

import uuid
from datetime import UTC, datetime

import factory
from factory import Faker

from src.models import JobStatus, MergeJob, PdfFile


class PdfFileFactory(factory.Factory):
    class Meta:
        model = PdfFile

    id = factory.LazyFunction(uuid.uuid4)
    filename = Faker("file_name", extension="pdf")
    s3_key = factory.LazyAttribute(lambda o: f"uploads/{o.id}.pdf")
    size_bytes = Faker("pyint", min_value=1024, max_value=5_000_000)
    page_count = Faker("pyint", min_value=1, max_value=50)
    uploaded_at = factory.LazyFunction(lambda: datetime.now(UTC))


class MergeJobFactory(factory.Factory):
    class Meta:
        model = MergeJob

    id = factory.LazyFunction(uuid.uuid4)
    status = JobStatus.pending
    source_file_ids = factory.LazyFunction(lambda: [str(uuid.uuid4()), str(uuid.uuid4())])
    output_s3_key = None
    error_message = None
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    completed_at = None
