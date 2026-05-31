# PDF Merger API

REST API that merges multiple PDF files into one. Final project for **Bulut & Konteyner Mimarisi** course.

> Detailed documentation: [docs/final-report.pdf](docs/final-report.pdf) · Architecture: [docs/architecture.png](docs/architecture.png)

## Stack

- **FastAPI** + **PostgreSQL** + **LocalStack S3** + **pypdf**
- **Docker** multi-stage + **docker-compose** + **Kubernetes** 
- **pytest** (unit + integration via Testcontainers) + **Playwright** (E2E) + **k6** (perf)
- **Prometheus** + **Grafana** + **OpenTelemetry** + **Jaeger**
- **GitHub Actions** CI/CD + **KEDA** autoscaling

## Quickstart (local)



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

Prerequisites

  Install these if you don't have them:
  - Minikube (https://minikube.sigs.k8s.io/docs/start/) — winget install Kubernetes.minikube
  - kubectl (https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/) — winget install Kubernetes.kubectl
  - Docker Desktop (Minikube uses it as the driver on Windows)


# minikube’un docker daemon’ına geç
eval $(minikube docker-env)

# imajı minikube içine build et
docker build -t pdf-merger-api:latest .

# deploy’u yeniden başlat
kubectl rollout restart deployment/pdf-merger-api






  # Step 1: Start Minikube
  minikube start --driver=docker --kubernetes-version=v1.32.0

  # minikube’un docker daemon’ına geç
  eval $(minikube docker-env)

  docker build -t pdf-merger-api:latest .

  # Step 3: Apply K8s manifests in order
  kubectl apply -f k8s/configmap.yaml
  kubectl apply -f k8s/secret.example.yaml
  kubectl apply -f k8s/postgres.yaml
  kubectl apply -f k8s/localstack.yaml

  kubectl wait --for=condition=ready pod -l app=postgres --timeout=180s
  kubectl wait --for=condition=ready pod -l app=localstack --timeout=180s

  kubectl apply -f k8s/deployment.yaml
  kubectl apply -f k8s/service.yaml
  kubectl rollout status deployment/pdf-merger-api --timeout=180s

  # Step 4: Prometheus + Grafana kurulumu
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
  helm repo update

  helm install monitoring prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace

  kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana -n monitoring --timeout=180s

  # Step 5: Access the API
  minikube service pdf-merger-api-np --url

  # Step 6: Access Grafana ve Prometheus (ayrı terminallerde çalıştır)
  kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
  kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090


  Step 6'yı iki ayrı PowerShell terminalinde çalıştır, ikisi de bloklayan komut. Sonra:
  - Grafana → http://localhost:3000 (user: admin, pass: kubectl --namespace monitoring get secret monitoring-grafana -o jsonpath="{.data.admin-password}" | base64 --decode) 
  - Prometheus → http://localhost:9090

# Step 7: Access PostgreSQL (ayrı terminallerde çalıştır)
  Önce port-forward aç:

  kubectl port-forward svc/postgres 5432:5432

  Sonra şifreyi öğren:

  kubectl get secret pdf-merger-secrets -o jsonpath="{.data.POSTGRES_PASSWORD}" | base64 --decode

  ---
  DBeaver'da New Connection → PostgreSQL:

  ┌──────────┬─────────────────────────┐
  │   Alan   │          Değer          │
  ├──────────┼─────────────────────────┤
  │ Host     │ localhost               │
  ├──────────┼─────────────────────────┤
  │ Port     │ 5432                    │
  ├──────────┼─────────────────────────┤
  │ Database │ pdfmerger               │
  ├──────────┼─────────────────────────┤
  │ Username │ pdfuser                 │
  ├──────────┼─────────────────────────┤
  │ Password │ üstteki komutun çıktısı │
  └──────────┴─────────────────────────┘

  Test Connection → bağlanmalı.

# Step 8: Apply KEDA

  # KEDA repo ekle
  helm repo add kedacore https://kedacore.github.io/charts
  helm repo update

  # KEDA'yı kur
  helm install keda kedacore/keda --namespace keda --create-namespace

  # Pod'ların ayağa kalkmasını bekle
  kubectl get pods -n keda --watch

  Hepsi Running olunca Ctrl+C ile çık, sonra:

  kubectl apply -f k8s/scaledobject.yaml

  Bu komutun çıktısını paylaş, scaledobject.keda.sh/pdf-merger-api created yazması lazım.


Grafana'da Dashboard Oluşturma

  http://localhost:3000 → sol menü → Dashboards → New → New Dashboard → Add visualization → datasource olarak Prometheus seç.

  Eklemek isteyeceğin paneller:

  1. Request Rate (req/s)
  sum(rate(http_requests_total{job="pdf-merger-api"}[2m]))

  2. Request Rate by Endpoint
  sum by (handler) (rate(http_requests_total{job="pdf-merger-api"}[2m]))

  3. Pod Sayısı (KEDA scaling)
  kube_deployment_status_replicas{deployment="pdf-merger-api"}

  4. HTTP p95 Latency
  histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="pdf-merger-api"}[2m])))
## Performance

Testi Çalıştırma

  Önce k6 kurulu mu kontrol et:

  k6 version

  Kurulu değilse:
  # Windows (Git Bash)
  choco install k6
  # veya
  winget install k6

  Sonra minikube URL'ini al ve testi çalıştır:

  # URL'i öğren
  minikube service pdf-merger-api-np --url

  # Testi çalıştır (URL'i değiştir)
  k6 run -e BASE_URL=http://192.168.49.2:30080 perf/load-test.js

  Test Ne Yapıyor?

  ┌────────────┬──────┬───────────┐
  │   Aşama    │ Süre │ VU Sayısı │
  ├────────────┼──────┼───────────┤
  │ Ramp up    │ 20s  │ 1 → 10    │
  ├────────────┼──────┼───────────┤
  │ Yük artışı │ 40s  │ 10 → 50   │
  ├────────────┼──────┼───────────┤
  │ Sabit yük  │ 30s  │ 50        │
  ├────────────┼──────┼───────────┤
  │ Ramp down  │ 10s  │ 50 → 0    │
  └────────────┴──────┴───────────┘

  Her VU: 2 PDF upload → merge → job polling yapıyor.

  KEDA'nın Tepkisini İzle

  Test çalışırken ayrı terminalde:

  kubectl get pods -l app=pdf-merger-api --watch

  50 VU ile 10 req/s eşiğini aşacak ve pod sayısının 1'den artmaya başladığını göreceksin.

## License

MIT — see [LICENSE](LICENSE).

## Author

- demirhan cakir
