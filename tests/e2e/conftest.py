"""E2E tests target a running API at $E2E_BASE_URL (default: http://localhost:8000)."""

import os

import pytest


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.getenv("E2E_BASE_URL", "http://localhost:8000")
