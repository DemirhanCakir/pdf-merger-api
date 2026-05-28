import pytest

pytestmark = pytest.mark.integration


def test_health_reports_db_and_s3_status(client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["s3"] == "ok"


def test_metrics_endpoint_exposes_prometheus_data(client) -> None:
    # Generate some traffic so counters exist
    client.get("/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "http_requests_total" in body or "http_request" in body
