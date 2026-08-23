import { describe, expect, it, vi } from "vitest";
import { FounderQueryError, formatPlatformFounderApiError, founderFailMessage, parseJsonArray } from "../platformFounderApi";

describe("parseJsonArray", () => {
  it("возвращает массив как есть", () => {
    expect(parseJsonArray<number>([1, 2])).toEqual([1, 2]);
  });

  it("возвращает пустой массив для не-массива", () => {
    expect(parseJsonArray({ a: 1 })).toEqual([]);
    expect(parseJsonArray(null)).toEqual([]);
    expect(parseJsonArray(undefined)).toEqual([]);
  });
});

describe("formatPlatformFounderApiError", () => {
  it("собирает строку из detail (string) и code", async () => {
    const r = {
      json: vi.fn().mockResolvedValue({ code: "platform_founder_jwt_not_configured", detail: "Disabled" }),
    } as unknown as Response;
    const msg = await formatPlatformFounderApiError(r, "fallback");
    expect(msg).toContain("platform_founder_jwt_not_configured");
    expect(msg).toContain("Disabled");
  });

  it("достаёт вложенный detail.message", async () => {
    const r = {
      json: vi.fn().mockResolvedValue({
        detail: { code: "totp_required", message: "Enroll first" },
      }),
    } as unknown as Response;
    const msg = await formatPlatformFounderApiError(r, "fallback");
    expect(msg).toContain("totp_required");
    expect(msg).toContain("Enroll first");
  });

  it("при не-JSON возвращает fallback", async () => {
    const r = {
      json: vi.fn().mockRejectedValue(new Error("not json")),
    } as unknown as Response;
    expect(await formatPlatformFounderApiError(r, "fallback")).toBe("fallback");
  });
});

describe("founderFailMessage", () => {
  const t = ((key: string, opts?: { status?: number }) => {
    if (key === "errors.status") return `HTTP ${opts?.status ?? 0}`;
    return key;
  }) as import("i18next").TFunction<"founder">;

  it("translates kind at render time without using Error.message", () => {
    expect(founderFailMessage(new FounderQueryError("session"), t)).toBe("errors.sessionInvalid");
    expect(founderFailMessage(new FounderQueryError("http", { httpStatus: 502 }), t)).toBe("HTTP 502");
  });

  it("prefers API detail when present", () => {
    expect(
      founderFailMessage(new FounderQueryError("unavailable", { apiDetail: "platform_disabled" }), t),
    ).toBe("platform_disabled");
  });
});
