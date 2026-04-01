import { describe, expect, it, vi, afterEach } from "vitest";
import { api, ApiErrorWithCode } from "@/api/client";

describe("api client CAPTCHA_REQUIRED parsing", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("extracts code from FastAPI detail object", async () => {
    const fetchMock = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          detail: { code: "CAPTCHA_REQUIRED", site_key: "site-key" },
        }),
        { status: 403, statusText: "Forbidden", headers: { "Content-Type": "application/json" } }
      );
    });
    globalThis.fetch = fetchMock;

    let err: unknown;
    try {
      await api.post("/v1/auth/send-code", { phone: "+79001234567" });
    } catch (e) {
      err = e;
    }
    expect(err).toBeInstanceOf(ApiErrorWithCode);
    const ae = err as ApiErrorWithCode;
    expect(ae.code).toBe("CAPTCHA_REQUIRED");
    expect(ae.details?.site_key).toBe("site-key");
  });
});

