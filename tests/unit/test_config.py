from src.config import Settings, get_settings


def test_settings_defaults_are_sensible() -> None:
    s = Settings()
    assert s.app_name == "pdf-merger-api"
    assert s.max_upload_size_mb > 0
    assert s.max_upload_bytes == s.max_upload_size_mb * 1024 * 1024


def test_settings_reads_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "7")
    monkeypatch.setenv("S3_BUCKET", "custom-bucket")
    get_settings.cache_clear()
    s = get_settings()
    assert s.max_upload_size_mb == 7
    assert s.s3_bucket == "custom-bucket"
    get_settings.cache_clear()


def test_factories_produce_distinct_uuids() -> None:
    from tests.factories import PdfFileFactory

    a = PdfFileFactory.build()
    b = PdfFileFactory.build()
    assert a.id != b.id
    assert a.filename.endswith(".pdf")
