# PDF Merger API

REST API that merges multiple PDF files into one. Final project for **Bulut & Konteyner Mimarisi** course.

> Detailed documentation: [docs/final-report.pdf](docs/final-report.pdf) · Architecture: [docs/architecture.png](docs/architecture.png)

## Stack

- **FastAPI** + **PostgreSQL** + **LocalStack S3** + **pypdf**
- **Docker** multi-stage + **docker-compose** + **Kubernetes** + **Helm**
- **pytest** (unit + integration via Testcontainers) + **Playwright** (E2E) + **k6** (perf)
- **Prometheus** + **Grafana** + **OpenTelemetry** + **Jaeger**
- **GitHub Actions** CI/CD + **KEDA** autoscaling

## Quickstart (local)

```bash
cp .env.example .env
docker compose up -d --build

# wait for healthchecks then visit:
#   http://localhost:8000/docs       # Swagger UI
#   http://localhost:3000            # Grafana (admin/admin)
#   http://localhost:9090            # Prometheus
#   http://localhost:16686           # Jaeger
```

Try a merge:

```bash
# upload two PDFs
FID1=$(curl -s -F "file=@sample1.pdf" http://localhost:8000/api/v1/files | jq -r .id)
FID2=$(curl -s -F "file=@sample2.pdf" http://localhost:8000/api/v1/files | jq -r .id)

# start a merge job
JID=$(curl -s -X POST http://localhost:8000/api/v1/merge \
    -H 'Content-Type: application/json' \
    -d "{\"file_ids\":[\"$FID1\",\"$FID2\"]}" | jq -r .id)

# poll status
curl -s http://localhost:8000/api/v1/jobs/$JID | jq

# download merged result
curl -OJ http://localhost:8000/api/v1/jobs/$JID/download
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/files` | Upload a PDF (multipart) |
| `GET`  | `/api/v1/files` | List uploaded PDFs |
| `POST` | `/api/v1/merge` | Start a merge job |
| `GET`  | `/api/v1/jobs/{id}` | Get job status |
| `GET`  | `/api/v1/jobs/{id}/download` | Download merged PDF |
| `GET`  | `/health` | DB + S3 health probe |
| `GET`  | `/metrics` | Prometheus metrics |

## Development

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# run tests
pytest --cov=src --cov-report=term-missing --cov-fail-under=70

# lint
ruff check . && ruff format --check .
```

## Deployment

```bash
# Kubernetes (Minikube)
minikube start
kubectl apply -f k8s/

# Helm
helm install pdf-merger ./charts/pdf-merger
```

## Performance

See [perf/report.md](perf/report.md) for k6 load test results and p95 latency analysis.

## License

MIT — see [LICENSE](LICENSE).

## Author

- demirhan — bireysel proje (individual)
