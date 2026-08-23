import { describe, expect, it } from "vitest";
import { catalogFetchErrorMessage, parsePublicCheckoutFailure } from "../platformBillingPublic";

/** Envelope as in `main.py` `http_exception_handler` for checkout / captcha. */
describe("parsePublicCheckoutFailure", () => {
  it("извлекает code, site_key из details и trace_id", () => {
    const r = parsePublicCheckoutFailure(403, {
      detail: "Требуется подтверждение Turnstile.",
      code: "captcha_required",
      details: { site_key: "0x4AAA" },
      trace_id: "tid-1",
    });
    expect(r.code).toBe("captcha_required");
    expect(r.siteKey).toBe("0x4AAA");
    expect(r.traceId).toBe("tid-1");
    expect(r.message).toContain("Turnstile");
  });

  it("маппит rate_limited на пользовательский текст", () => {
    const r = parsePublicCheckoutFailure(429, {
      detail: "Слишком много запросов",
      code: "rate_limited",
    });
    expect(r.code).toBe("rate_limited");
    expect(r.message).toContain("Too many requests");
  });
});

describe("catalogFetchErrorMessage", () => {
  it("does not surface empty JSON as Catalog Unavailable {}", () => {
    expect(catalogFetchErrorMessage(500, "")).toContain("Could not load the plan catalog");
    expect(catalogFetchErrorMessage(502, "{}")).toContain("Could not load the plan catalog");
    expect(catalogFetchErrorMessage(0, "")).toContain("Could not load the plan catalog");
  });

  it("keeps a structured 4xx detail", () => {
    const msg = catalogFetchErrorMessage(
      429,
      JSON.stringify({ detail: "Too many catalog requests", code: "rate_limited" }),
    );
    expect(msg).toContain("Too many catalog requests");
  });
});
