import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { API_BASE, API_STORAGE_KEYS } from "@/api/client";

const __dirname = dirname(fileURLToPath(import.meta.url));
const srcRoot = join(__dirname, "..");
const frontendRoot = join(__dirname, "../..");

/**
 * Регрессия стабильных контрактов HTTP-клиента и оболочек маршрутизации.
 * Инварианты транспорта и зон приложения — по коду `api/client.ts`, `App.tsx`, `routePaths.ts`.
 */
describe("API client and app shell invariants", () => {
  it("API_BASE stays /api (HTTP bridge prefix)", () => {
    expect(API_BASE).toBe("/api");
  });

  it("API_STORAGE_KEYS registry is stable (admin / patient token semantics)", () => {
    expect(Object.keys(API_STORAGE_KEYS).sort()).toEqual(
      ["adminClinicId", "adminId", "adminToken", "patientId", "patientToken"].sort()
    );
    expect(Object.values(API_STORAGE_KEYS).sort()).toEqual(
      [
        "dental_booking_admin_clinic_id",
        "dental_booking_admin_id",
        "dental_booking_admin_token",
        "dental_booking_patient_id",
        "dental_booking_patient_token",
      ].sort()
    );
  });

  it("App.tsx keeps ordered admin shell: dashboard route → AuthGuard → ClinicProvider → AdminLayout", () => {
    const appSrc = readFileSync(join(srcRoot, "App.tsx"), "utf8");
    const adminDashboard = appSrc.indexOf("ROUTE_PATHS.admin.dashboard");
    const guard = appSrc.indexOf("<AdminAuthGuard");
    const clinic = appSrc.indexOf("<AdminClinicProvider");
    const layout = appSrc.indexOf("<AdminLayout");
    expect(adminDashboard, "admin dashboard route present").toBeGreaterThanOrEqual(0);
    expect(adminDashboard < guard && guard < clinic && clinic < layout, "admin shell order").toBe(true);
  });

  it("App.tsx: /app home route wraps AppLayout with PatientAuthProvider in element prop", () => {
    const appSrc = readFileSync(join(srcRoot, "App.tsx"), "utf8");
    expect(appSrc).toMatch(
      /path=\{ROUTE_PATHS\.patient\.home\}[\s\S]*?element=\{[\s\S]*?<PatientAuthProvider>[\s\S]*?<AppLayout\s*\/>[\s\S]*?<\/PatientAuthProvider>/
    );
  });

  it("App.tsx still references core guards and layouts", () => {
    const appSrc = readFileSync(join(srcRoot, "App.tsx"), "utf8");
    expect(appSrc, "admin shell chain").toMatch(/AdminAuthGuard/);
    expect(appSrc, "admin clinic context").toMatch(/AdminClinicProvider/);
    expect(appSrc, "admin layout").toMatch(/AdminLayout/);
    expect(appSrc, "patient zone").toMatch(/PatientAuthProvider/);
    const routerCalls = appSrc.match(/createBrowserRouter\s*\(/g);
    expect(routerCalls?.length ?? 0, "single createBrowserRouter() root").toBe(1);
  });

  it("vite dev proxy keeps /api prefix (align with deploy)", () => {
    const vite = readFileSync(join(frontendRoot, "vite.config.ts"), "utf8");
    expect(vite).toMatch(/proxy:\s*\{[\s\S]*?"\/api"\s*:\s*\{/);
  });
});
