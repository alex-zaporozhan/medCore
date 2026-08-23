import type { ReactElement, ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import i18n, { UI_LOCALE_STORAGE_KEY } from "@/i18n";
import { renderWithI18n } from "@/i18n/testUtils";
import { ROUTE_PATHS } from "@/routePaths";
import AdminLayout from "../AdminLayout";

vi.mock("@/contexts/AdminClinicContext", () => ({
  useAdminClinic: () => ({
    clinics: [{ id: "clinic-1", name: "Demo Clinic" }],
    selectableClinics: [{ id: "clinic-1", name: "Demo Clinic" }],
    currentClinicId: "clinic-1",
    setCurrentClinicId: vi.fn(),
    isClinicScopeLocked: false,
    error: null,
    isLoading: false,
  }),
}));

vi.mock("@/hooks/useAdminOmniChat", () => ({
  useAdminOmniChats: () => ({ data: { items: [] } }),
}));

vi.mock("@/hooks/useAdminSearch", () => ({
  useAdminSearch: () => ({ data: { items: [] } }),
}));

vi.mock("@/hooks/useAiAgent", () => ({
  useAiAgent: () => ({ isPending: false, mutate: vi.fn(), data: undefined }),
}));

vi.mock("@/shared/aiFeatures", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/shared/aiFeatures")>();
  return {
    ...actual,
    useAiFeatures: () => ({
      get: () => ({ id: "omni.spotlight.agent", status: "stub" }),
    }),
  };
});

vi.mock("@/hooks/useAdminSession", () => ({
  useAdminSession: () => ({
    data: {
      permissions: ["patients.pii.read", "rbac.manage"],
      roles: ["owner"],
      entitlement_enforced: false,
    },
  }),
}));

vi.mock("@/admin/components/AdminOwnerSubscriptionStrip", () => ({
  AdminOwnerSubscriptionStrip: () => null,
}));

function wrap(ui: ReactNode): ReactElement {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return (
    <MantineProvider>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[ROUTE_PATHS.admin.dashboard]}>
          <Routes>
            <Route element={ui}>
              <Route path={ROUTE_PATHS.admin.dashboard} element={<div>outlet</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>
  );
}

describe("AdminLayout nav i18n", () => {
  afterEach(async () => {
    localStorage.removeItem(UI_LOCALE_STORAGE_KEY);
    localStorage.removeItem("admin_navbar_collapsed");
    await i18n.changeLanguage("en");
  });

  it("renders nav labels from nav.json, not blank keys", async () => {
    await renderWithI18n(wrap(<AdminLayout />), { locale: "en" });
    expect(screen.getByText("Feed")).toBeTruthy();
    expect(screen.getAllByText("Staff").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Language")).toBeTruthy();
    expect(screen.queryByText("Лента")).toBeNull();
  });

  it("keeps the locale switch reachable when the navbar is collapsed", async () => {
    localStorage.setItem("admin_navbar_collapsed", "true");
    await renderWithI18n(wrap(<AdminLayout />), { locale: "en" });
    expect(screen.getByLabelText("Language")).toBeTruthy();
  });
});
