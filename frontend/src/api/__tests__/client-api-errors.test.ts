import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiErrorWithCode, api } from "../client";

describe("parseFastApiErrorBody (via api + fetch mock)", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("422: detail array yields readable message (validation)", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 422,
      statusText: "Unprocessable Entity",
      text: async () =>
        JSON.stringify({
          detail: [
            { loc: ["body", "phone"], msg: "field required", type: "value_error.missing" },
            { loc: ["body", "email"], msg: "invalid format", type: "value_error" },
          ],
        }),
    });

    try {
      await api.get("/v1/x");
      expect.fail("expected throw");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiErrorWithCode);
      const err = e as ApiErrorWithCode;
      expect(err.name).toBe("ApiErrorWithCode");
      expect(err.message).toContain("phone");
      expect(err.message).toContain("email");
    }
  });

  it("uses top-level message when detail absent", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 500,
      statusText: "Error",
      text: async () => JSON.stringify({ message: "Upstream failure" }),
    });

    try {
      await api.get("/v1/y");
      expect.fail("expected throw");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiErrorWithCode);
      expect((e as ApiErrorWithCode).message).toContain("Upstream failure");
    }
  });
});
