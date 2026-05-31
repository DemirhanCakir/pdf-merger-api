"""Shared fixtures: Testcontainers Postgres + LocalStack S3 + FastAPI TestClient."""

from __future__ import annotations

import os
from collections.abc import Iterator

import boto3
import pytest
from botocore.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---------- session-scoped infra ----------


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """Spin up a Postgres container for integration tests.

    If TEST_DATABASE_URL is set (e.g. in CI with a service container), use that instead
    to avoid the cost of Testcontainers startup.
    """
    env_url = os.getenv("TEST_DATABASE_URL")
    if env_url:
        yield env_url
        return

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as pg:
        # testcontainers default driver is psycopg2; normalize the URL just in case
        raw = pg.get_connection_url()
        if raw.startswith("postgresql://"):
            raw = raw.replace("postgresql://", "postgresql+psycopg2://", 1)
        yield raw


@pytest.fixture(scope="session")
def localstack_endpoint() -> Iterator[str]:
    env_url = os.getenv("TEST_S3_ENDPOINT_URL")
    if env_url:
        yield env_url
        return

    from testcontainers.localstack import LocalStackContainer

    with LocalStackContainer(image="localstack/localstack:3.8").with_services("s3") as ls:
        yield ls.get_url()


# ---------- per-test wiring ----------


@pytest.fixture
def settings_override(monkeypatch, postgres_url: str, localstack_endpoint: str):
    """Reset cached settings + s3 client so each test sees the test endpoints."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("S3_ENDPOINT_URL", localstack_endpoint)
    monkeypatch.setenv("S3_BUCKET", "pdf-merger-test")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("OTEL_ENABLED", "false")

    from src import config as config_mod
    from src.services import s3_client as s3_mod

    config_mod.get_settings.cache_clear()
    s3_mod.get_s3_client.cache_clear()
    yield config_mod.get_settings()
    config_mod.get_settings.cache_clear()
    s3_mod.get_s3_client.cache_clear()


@pytest.fixture
def s3_bucket(settings_override) -> str:
    """Create the test bucket fresh for each test (delete + recreate)."""
    client = boto3.client(
        "s3",
        endpoint_url=settings_override.s3_endpoint_url,
        region_name=settings_override.s3_region,
        aws_access_key_id=settings_override.aws_access_key_id,
        aws_secret_access_key=settings_override.aws_secret_access_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    bucket = settings_override.s3_bucket

    # cleanup any leftover objects from a prior test
    try:
        objs = client.list_objects_v2(Bucket=bucket).get("Contents", [])
        for o in objs:
            client.delete_object(Bucket=bucket, Key=o["Key"])
        client.delete_bucket(Bucket=bucket)
    except client.exceptions.ClientError:
        pass

    client.create_bucket(Bucket=bucket)
    return bucket


@pytest.fixture
def db_engine(settings_override):
    """Create a fresh DB schema for each test (drop + create_all)."""
    from src import db as db_mod
    from src.models import MergeJob, PdfFile  # noqa: F401

    engine = create_engine(settings_override.database_url, future=True)
    db_mod.Base.metadata.drop_all(bind=engine)
    db_mod.Base.metadata.create_all(bind=engine)

    db_mod._engine = engine
    db_mod._SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False, future=True)
    s = Session()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def client(db_engine, s3_bucket) -> Iterator[TestClient]:
    """FastAPI TestClient wired to test DB + test S3."""
    from src.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c
