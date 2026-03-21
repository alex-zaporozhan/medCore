/**
 * Wave 5 (A4/A21): smoke + optional authenticated ERP dashboard GET.
 *
 *   k6 run -e BASE_URL=http://localhost:8000 scripts/loadtests/k6_wave5_smoke.js
 *
 * Staging / load (set secrets in CI or env):
 *   -e ADMIN_TOKEN=... -e ADMIN_CLINIC_ID=uuid
 */
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 3,
  duration: "20s",
  thresholds: {
    http_req_duration: ["p(95)<10000"],
  },
};

export default function () {
  const base = __ENV.BASE_URL || "http://127.0.0.1:8000";
  const root = base.replace(/\/$/, "");
  const res = http.get(`${root}/health`);
  check(res, { "health 200": (r) => r.status === 200 });

  const tok = __ENV.ADMIN_TOKEN;
  const cid = __ENV.ADMIN_CLINIC_ID;
  if (tok && cid) {
    const today = new Date().toISOString().slice(0, 10);
    const r2 = http.get(
      `${root}/api/v1/admin/clinics/${cid}/reports/dashboard?date=${today}&period=day`,
      {
        headers: { Authorization: `Bearer ${tok}` },
        tags: { name: "admin_reports_dashboard" },
      }
    );
    check(r2, {
      "dashboard ok": (r) =>
        r.status === 200 || r.status === 403 || r.status === 404,
    });
  }

  sleep(0.3);
}
