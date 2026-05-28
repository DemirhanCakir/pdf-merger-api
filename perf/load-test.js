// k6 load test for pdf-merger-api.
//
// Scenario: ramp up to 50 virtual users, each uploading two small PDFs and
// triggering a merge job, then polling the job until completion.
//
// Run locally:
//   k6 run -e BASE_URL=http://localhost:8000 perf/load-test.js
// Or against a deployed cluster:
//   k6 run -e BASE_URL=http://pdf-merger.local perf/load-test.js
//
// Outputs p95 latency for HTTP requests; see perf/report.md for analysis.

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Trend, Rate } from 'k6/metrics';
import encoding from 'k6/encoding';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Pre-built minimal valid PDF (1 blank page). Generated once and reused.
const TINY_PDF_B64 =
  'JVBERi0xLjQKMSAwIG9iago8PC9UeXBlIC9DYXRhbG9nIC9QYWdlcyAyIDAgUj4+CmVuZG9iagoy' +
  'IDAgb2JqCjw8L1R5cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50IDE+PgplbmRvYmoKMyAw' +
  'IG9iago8PC9UeXBlIC9QYWdlIC9QYXJlbnQgMiAwIFIgL01lZGlhQm94IFswIDAgNTk1IDg0Ml0g' +
  'L1Jlc291cmNlcyA8PD4+IC9Db250ZW50cyA0IDAgUj4+CmVuZG9iago0IDAgb2JqCjw8L0xlbmd0' +
  'aCAwPj4Kc3RyZWFtCmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDUKMDAwMDAwMDAwMCA2NTUzNSBm' +
  'IAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTggMDAwMDAgbiAKMDAwMDAwMDExNSAwMDAw' +
  'MCBuIAowMDAwMDAwMjA1IDAwMDAwIG4gCnRyYWlsZXIKPDwvU2l6ZSA1IC9Sb290IDEgMCBSPj4K' +
  'c3RhcnR4cmVmCjI0NQolJUVPRgo=';
const TINY_PDF = encoding.b64decode(TINY_PDF_B64);

export const options = {
  thresholds: {
    http_req_failed: ['rate<0.05'],            // <5% errors
    http_req_duration: ['p(95)<2000'],         // p95 under 2s
    merge_total_duration: ['p(95)<10000'],     // p95 full merge flow under 10s
  },
  scenarios: {
    upload_merge: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '20s', target: 10 },
        { duration: '40s', target: 50 },
        { duration: '30s', target: 50 },
        { duration: '10s', target: 0 },
      ],
      gracefulRampDown: '15s',
    },
  },
};

const mergeDuration = new Trend('merge_total_duration', true);
const mergeSuccess = new Rate('merge_success_rate');

function uploadPdf() {
  const payload = {
    file: http.file(TINY_PDF, 'tiny.pdf', 'application/pdf'),
  };
  const resp = http.post(`${BASE_URL}/api/v1/files`, payload);
  check(resp, { 'upload 201': (r) => r.status === 201 });
  return resp.status === 201 ? resp.json('id') : null;
}

export default function () {
  let jobOk = false;
  const start = Date.now();

  group('upload-merge-poll', () => {
    const a = uploadPdf();
    const b = uploadPdf();
    if (!a || !b) {
      mergeSuccess.add(false);
      return;
    }

    const mergeResp = http.post(
      `${BASE_URL}/api/v1/merge`,
      JSON.stringify({ file_ids: [a, b] }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    check(mergeResp, { 'merge 202': (r) => r.status === 202 });
    if (mergeResp.status !== 202) {
      mergeSuccess.add(false);
      return;
    }
    const jobId = mergeResp.json('id');

    // Poll for completion (up to ~5s)
    for (let i = 0; i < 10; i++) {
      sleep(0.5);
      const statusResp = http.get(`${BASE_URL}/api/v1/jobs/${jobId}`);
      const status = statusResp.json('status');
      if (status === 'completed') {
        jobOk = true;
        break;
      }
      if (status === 'failed') break;
    }
  });

  mergeDuration.add(Date.now() - start);
  mergeSuccess.add(jobOk);
  sleep(1);
}
