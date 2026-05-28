"""End-to-end tests driving the Swagger UI in a real browser.

Targets a running instance of the API (docker-compose / minikube / k8s deploy).
Run with: pytest tests/e2e/ --browser chromium
"""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_swagger_ui_loads_and_shows_title(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/docs", wait_until="networkidle")
    expect(page).to_have_title("pdf-merger-api - Swagger UI")
    expect(page.locator("h2.title")).to_contain_text("pdf-merger-api")


def test_swagger_ui_lists_all_business_endpoints(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/docs", wait_until="networkidle")

    body = page.locator("body").inner_text()
    assert "/api/v1/files" in body
    assert "/api/v1/merge" in body
    assert "/api/v1/jobs/{job_id}" in body
    assert "/health" in body


def test_swagger_ui_can_expand_upload_endpoint(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/docs", wait_until="networkidle")

    # Click the POST /api/v1/files row to expand it
    upload = page.locator("#operations-files-upload_file_api_v1_files_post")
    upload.click()
    expect(upload.locator(".opblock-section")).to_be_visible()


def test_health_endpoint_returns_ok_via_api_request(page: Page, base_url: str) -> None:
    resp = page.request.get(f"{base_url}/health")
    assert resp.ok
    body = resp.json()
    assert body["status"] in {"ok", "degraded"}
    assert "database" in body
    assert "s3" in body


def test_unknown_job_id_returns_404_via_api_request(page: Page, base_url: str) -> None:
    resp = page.request.get(f"{base_url}/api/v1/jobs/00000000-0000-0000-0000-000000000000")
    assert resp.status == 404
