import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { API_STORAGE_KEYS, shouldClearPatientSessionOn401 } from "../client";

describe("shouldClearPatientSessionOn401", () => {
  it("/v1/patient/* only with session hint (Bearer or storage)", () => {
    expect(shouldClearPatientSessionOn401("/v1/patient/me", null)).toBe(false);
    expect(shouldClearPatientSessionOn401("/v1/patient/bookings?x=1", "t")).toBe(true);
    localStorage.setItem(API_STORAGE_KEYS.patientToken, "stored");
    expect(shouldClearPatientSessionOn401("/v1/patient/me", null)).toBe(true);
    localStorage.removeItem(API_STORAGE_KEYS.patientToken);
  });

  it("matches /v1/payments only when Bearer was sent", () => {
    expect(shouldClearPatientSessionOn401("/v1/payments", null)).toBe(false);
    expect(shouldClearPatientSessionOn401("/v1/payments", "tok")).toBe(true);
    expect(shouldClearPatientSessionOn401("/v1/payments?return_url=x", "tok")).toBe(true);
  });

  it("matches other paths when token equals stored patient token", () => {
    localStorage.setItem(API_STORAGE_KEYS.patientToken, "same");
    expect(shouldClearPatientSessionOn401("/v1/any/future", "same")).toBe(true);
    expect(shouldClearPatientSessionOn401("/v1/any/future", "other")).toBe(false);
    localStorage.removeItem(API_STORAGE_KEYS.patientToken);
  });
});

describe("api client 401 patient session", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 401,
        statusText: "Unauthorized",
        text: async () => JSON.stringify({ detail: "expired" }),
      })
    );
    vi.stubGlobal("location", {
      ...window.location,
      pathname: "/app/booking",
      href: "http://localhost/app/booking",
      assign: vi.fn(),
      replace: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    globalThis.fetch = originalFetch;
    localStorage.clear();
  });

  it("clears patient storage on 401 for POST /v1/payments with token", async () => {
    const { api } = await import("../client");
    const remove = vi.spyOn(Storage.prototype, "removeItem");
    await expect(
      api.post("/v1/payments", { booking_id: "00000000-0000-0000-0000-000000000001" }, "patient-jwt")
    ).rejects.toThrow();
    expect(remove).toHaveBeenCalledWith(API_STORAGE_KEYS.patientToken);
    expect(remove).toHaveBeenCalledWith(API_STORAGE_KEYS.patientId);
  });

  it("does not clear patient storage on 401 /v1/patient/me without session hint", async () => {
    const { api } = await import("../client");
    const remove = vi.spyOn(Storage.prototype, "removeItem");
    await expect(api.get("/v1/patient/me")).rejects.toThrow();
    expect(remove).not.toHaveBeenCalledWith(API_STORAGE_KEYS.patientToken);
    expect(remove).not.toHaveBeenCalledWith(API_STORAGE_KEYS.patientId);
  });
});
