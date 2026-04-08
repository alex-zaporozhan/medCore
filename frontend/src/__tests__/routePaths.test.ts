import { describe, expect, it } from "vitest";
import {
  ADMIN_SHELL_ROUTE_SEGMENTS,
  ALL_PUBLIC_APP_PATHS,
  PATIENT_APP_ROUTE_SEGMENTS,
  ROUTE_PATHS,
  buildDerivedPublicAppPaths,
} from "@/routePaths";
import {
  isAdminLoginPath,
  isClinicScopedPatientSignInPath,
  isPatientLoginPath,
  matchesPatternPath,
  normalizePathname,
} from "@/routePathUtils";

describe("routePaths (public URL canon)", () => {
  it("lists unique public paths", () => {
    const set = new Set(ALL_PUBLIC_APP_PATHS);
    expect(set.size).toBe(ALL_PUBLIC_APP_PATHS.length);
  });

  it("derived list matches ROUTE_PATHS / сегменты (паритет канона)", () => {
    const fromObjects = new Set([
      ...Object.values(ROUTE_PATHS.marketing),
      ...Object.values(ROUTE_PATHS.platform),
      ...Object.values(ROUTE_PATHS.admin),
      ...Object.values(ROUTE_PATHS.patient),
      ...Object.values(ROUTE_PATHS.other),
    ]);
    expect(fromObjects).toEqual(new Set(ALL_PUBLIC_APP_PATHS));
    expect(new Set(buildDerivedPublicAppPaths())).toEqual(new Set(ALL_PUBLIC_APP_PATHS));
  });

  it("ADMIN_SHELL_ROUTE_SEGMENTS покрывают /admin/* в ROUTE_PATHS (кроме login и dashboard)", () => {
    for (const seg of ADMIN_SHELL_ROUTE_SEGMENTS) {
      expect(Object.values(ROUTE_PATHS.admin)).toContain(`/admin/${seg}`);
    }
  });

  it("PATIENT_APP_ROUTE_SEGMENTS покрывают /app/* в ROUTE_PATHS (кроме home)", () => {
    for (const seg of PATIENT_APP_ROUTE_SEGMENTS) {
      expect(Object.values(ROUTE_PATHS.patient)).toContain(`/app/${seg}`);
    }
  });

  it("keeps zone prefixes stable", () => {
    expect(ROUTE_PATHS.admin.dashboard.startsWith("/admin")).toBe(true);
    expect(ROUTE_PATHS.admin.login.startsWith("/admin")).toBe(true);
    expect(ROUTE_PATHS.patient.home.startsWith("/app")).toBe(true);
    expect(ROUTE_PATHS.marketing.landing).toBe("/");
  });
});

describe("routePathUtils", () => {
  it("normalizePathname strips trailing slash", () => {
    expect(normalizePathname("/login/")).toBe("/login");
    expect(normalizePathname("/")).toBe("/");
  });

  it("matchesPatternPath accepts /login и /login/", () => {
    expect(matchesPatternPath("/login", ROUTE_PATHS.other.login)).toBe(true);
    expect(matchesPatternPath("/login/", ROUTE_PATHS.other.login)).toBe(true);
  });

  it("isPatientLoginPath / isAdminLoginPath — единая семантика зон входа", () => {
    expect(isPatientLoginPath("/login")).toBe(true);
    expect(isPatientLoginPath("/login/")).toBe(true);
    expect(isPatientLoginPath("/sign-in")).toBe(false);
    expect(isPatientLoginPath("/sign-in/")).toBe(false);
    expect(isClinicScopedPatientSignInPath("/c/my-clinic/sign-in")).toBe(true);
    expect(isPatientLoginPath("/c/my-clinic/sign-in")).toBe(true);
    expect(isPatientLoginPath("/app")).toBe(false);
    expect(isAdminLoginPath("/admin/login")).toBe(true);
    expect(isAdminLoginPath("/admin/login/")).toBe(true);
    expect(isAdminLoginPath("/admin")).toBe(false);
  });
});
