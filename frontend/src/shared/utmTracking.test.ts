import { describe, it, expect, beforeEach, vi } from "vitest";
import { getCurrentUtm, useUtmTracking } from "./utmTracking";

const STORAGE_KEY = "marketing.utm";

describe("utmTracking helpers", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    (global as any).window = {
      location: {
        href: "https://example.com/?utm_source=google&utm_medium=cpc&utm_campaign=camp&utm_content=ad&utm_term=kw",
        pathname: "/",
        search: "?utm_source=google&utm_medium=cpc&utm_campaign=camp&utm_content=ad&utm_term=kw",
        hash: "#hero",
      },
      localStorage: {
        store: {} as Record<string, string>,
        getItem(key: string) {
          return this.store[key] ?? null;
        },
        setItem(key: string, value: string) {
          this.store[key] = value;
        },
        removeItem(key: string) {
          delete this.store[key];
        },
      },
      crypto: {
        randomUUID: () => "test-session-id",
      },
    } as any;
  });

  it("captures UTM params and stores them with session_id", () => {
    useUtmTracking();
    const raw = (window as any).localStorage.getItem(STORAGE_KEY);
    expect(raw).toBeTruthy();
    const parsed = JSON.parse(raw!);
    expect(parsed.session_id).toBe("test-session-id");
    expect(parsed.utm_source).toBe("google");
    expect(parsed.utm_medium).toBe("cpc");
    expect(parsed.utm_campaign).toBe("camp");
    expect(parsed.utm_content).toBe("ad");
    expect(parsed.utm_term).toBe("kw");
    expect(parsed.landing_page).toBe("/?utm_source=google&utm_medium=cpc&utm_campaign=camp&utm_content=ad&utm_term=kw");
    expect(parsed.anchor).toBe("#hero");
  });

  it("getCurrentUtm returns stored context", () => {
    const ctx = {
      session_id: "existing-id",
      utm_source: "yandex",
      landing_page: "/",
      anchor: null,
    };
    (window as any).localStorage.setItem(STORAGE_KEY, JSON.stringify(ctx));
    const result = getCurrentUtm();
    expect(result).toEqual(ctx);
  });
});

