// Minimal k6 smoke test for CI — single VU, ~10 iterations, just verifies the
// API is reachable and basic endpoints respond. Used in the `smoke` GitHub
// Actions stage after `deploy`.

import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
  vus: 1,
  iterations: 10,
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1000'],
  },
};

export default function () {
  const health = http.get(`${BASE_URL}/health`);
  check(health, { 'health 200': (r) => r.status === 200 });

  const list = http.get(`${BASE_URL}/api/v1/files`);
  check(list, { 'list 200': (r) => r.status === 200 });

  const metrics = http.get(`${BASE_URL}/metrics`);
  check(metrics, { 'metrics 200': (r) => r.status === 200 });
}
