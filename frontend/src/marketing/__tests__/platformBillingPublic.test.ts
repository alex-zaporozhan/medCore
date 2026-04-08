import { describe, expect, it } from "vitest";
import { parsePublicCheckoutFailure } from "../platformBillingPublic";

/** Envelope как в `main.py` `http_exception_handler` для checkout / captcha. */
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
    expect(r.message).toContain("Слишком много запросов");
  });
});
