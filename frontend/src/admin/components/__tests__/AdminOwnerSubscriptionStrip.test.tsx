import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter } from "react-router-dom";
import { renderWithI18n } from "@/i18n/testUtils";
import { AdminOwnerSubscriptionStrip } from "../AdminOwnerSubscriptionStrip";

vi.mock("@/hooks/useAdminSession", () => ({
  useAdminSession: () => ({
    data: {
      organization_id: "org-1",
      roles: ["owner"],
      entitlement_enforced: true,
      entitlement_keys: ["sku-a", "sku-b"],
    },
  }),
}));

describe("AdminOwnerSubscriptionStrip A1", () => {
  it("shows EN tariff summary with plural count", async () => {
    await renderWithI18n(
      <MantineProvider>
        <MemoryRouter>
          <AdminOwnerSubscriptionStrip />
        </MemoryRouter>
      </MantineProvider>,
      { locale: "en" },
    );
    expect(screen.getByText("Plan: 2 options in the subscription")).toBeTruthy();
    expect(screen.getByText("Subscription →")).toBeTruthy();
  });
});
