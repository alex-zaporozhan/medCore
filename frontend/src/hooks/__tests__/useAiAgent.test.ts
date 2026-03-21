import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { createElement } from "react";

const postMock = vi.fn();

vi.mock("@/api/client", () => ({
  api: {
    post: (...args: unknown[]) => postMock(...args),
  },
  getAdminToken: () => "token",
}));

vi.mock("@/contexts/AdminClinicContext", () => ({
  useAdminClinic: () => ({
    currentClinicId: "clinic-1",
  }),
}));

describe("useAiAgent", () => {
  beforeEach(() => {
    postMock.mockReset();
    vi.resetModules();
  });

  it("returns stub answer without network when feature is stub", async () => {
    vi.doMock("@/shared/aiFeatures", () => ({
      useAiFeatures: () => ({
        get: () => ({ id: "omni.spotlight.agent", label: "Spotlight", status: "stub" }),
      }),
    }));

    const { useAiAgent } = await import("../useAiAgent");
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children);
    const { result } = renderHook(() => useAiAgent(), { wrapper });

    await act(async () => {
      const res = await result.current.mutateAsync({ query: "Привет" });
      expect(res.answer).toContain("stub");
    });

    expect(postMock).not.toHaveBeenCalled();
  });

  it("calls backend when feature is beta", async () => {
    vi.doMock("@/shared/aiFeatures", () => ({
      useAiFeatures: () => ({
        get: () => ({ id: "omni.spotlight.agent", label: "Spotlight", status: "beta" }),
      }),
    }));

    postMock.mockResolvedValueOnce({ answer: "ok" });

    const { useAiAgent } = await import("../useAiAgent");
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children);
    const { result } = renderHook(() => useAiAgent(), { wrapper });

    await act(async () => {
      const res = await result.current.mutateAsync({ query: "Привет" });
      expect(res.answer).toBe("ok");
    });

    expect(postMock).toHaveBeenCalled();
  });
});

