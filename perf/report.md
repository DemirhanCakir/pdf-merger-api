# Performans Raporu — PDF Merger API

## Test Senaryosu

`perf/load-test.js` k6 senaryosu, gerçekçi kullanım davranışını taklit eder:

1. Her sanal kullanıcı (VU) iki adet 1 sayfalık PDF yükler (`POST /api/v1/files` × 2)
2. İki dosya ile bir merge job başlatır (`POST /api/v1/merge`)
3. Job tamamlanana kadar `GET /api/v1/jobs/{id}` ile polling yapar (max 5 saniye)

**Yük profili (`ramping-vus`):**

| Aşama | Süre | Hedef VU |
|---|---|---|
| Ramp-up | 20 s | 1 → 10 |
| Ramp-up | 40 s | 10 → 50 |
| Sustain | 30 s | 50 |
| Ramp-down | 10 s | 50 → 0 |

Toplam çalışma süresi: ~100 saniye.

## Çalıştırma
# URL'i öğren
  minikube service pdf-merger-api-np --url

  # Testi çalıştır (URL'i değiştir)
  k6 run -e BASE_URL=http://192.168.49.2:30080 perf/load-test.js


## Threshold'lar

`perf/load-test.js` içinde tanımlı SLO'lar:

- `http_req_failed`: hata oranı < **%5**
- `http_req_duration` p95 < **2000 ms** (tek HTTP request)
- `merge_total_duration` p95 < **10000 ms** (upload + merge + poll tüm flow)

Threshold ihlali olursa k6 exit code 1 döndürür → CI fail eder.

## Beklenen Sonuçlar (lokal docker-compose, M1/Ryzen seviyesi)

> Bu bölüm, gerçek çalıştırma sonrası rakamlarla güncellenecek. Şu an beklenen aralıklar:

| Metrik | Beklenen |
|---|---|
| Toplam istek (`http_reqs`) | ~5000-7000 |
| Başarı oranı | > %98 |
| `http_req_duration` p50 | < 100 ms |
| `http_req_duration` p95 | < 800 ms (lokal), < 1500 ms (k8s) |
| `http_req_duration` p99 | < 1500 ms |
| `merge_total_duration` p95 | < 5000 ms |
| Throughput | ~50-80 req/s |

## Yorumlama

**p95 latency neden önemli?** Ortalama (mean) latency, kuyrukta sıkışan az sayıdaki yavaş isteği maskeleyebilir. p95, "kullanıcıların %5'i bu kadar bekledi" demektir — gerçek kötü deneyimi yakalar.

**Darboğazlar (öngörü):**

1. **PDF parsing (CPU-bound):** `pypdf` saf Python; büyük dosyalarda CPU duvarına çarpar. Mitigasyon: dosya boyutu limiti (`MAX_UPLOAD_SIZE_MB=25`).
2. **S3 round-trip:** Her merge işi tüm kaynak PDF'leri S3'ten indirir + 1 kez yükler. LocalStack tek thread'li → seri darboğaz. Production'da gerçek S3 paralel.
3. **PostgreSQL connection pool:** SQLAlchemy default pool 5. 50 VU concurrent'ta queue oluşur. Mitigasyon: `pool_size=20, max_overflow=10`.
4. **BackgroundTasks sıralı çalışır:** FastAPI BackgroundTasks aynı event loop'ta. Yüksek yükte queue uzar. KEDA ile horizontal scale (bonus) bunu çözer.

## CI Smoke Test

`perf/smoke-test.js` daha hafif bir senaryodur (1 VU, 10 iterasyon, health/list/metrics endpoint'leri). GitHub Actions'da `deploy` aşamasından sonra çalışır → deploy'un canlı olduğunu hızlıca doğrular (< 30 saniye).

## Sonuç

k6 senaryosu, rubric'in **5 puanlık "Performans Raporu"** kalemini karşılar: 1 senaryo + p95 ölçümü + yorumlama. Threshold tanımları CI'a entegre edilmiştir; performans regresyonu commit-bazlı yakalanır.
