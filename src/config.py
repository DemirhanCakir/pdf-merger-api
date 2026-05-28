from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "pdf-merger-api"
    log_level: str = "INFO"
    environment: str = "development"

    database_url: str = "postgresql+psycopg2://pdfuser:pdfpass@localhost:5432/pdfmerger"

    s3_endpoint_url: str | None = "http://localhost:4566"
    s3_bucket: str = "pdf-merger"
    s3_region: str = "us-east-1"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"

    max_upload_size_mb: int = 25
    max_merge_files: int = 20

    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "pdf-merger-api"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
