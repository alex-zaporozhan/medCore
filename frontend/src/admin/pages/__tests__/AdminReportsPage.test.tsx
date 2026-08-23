import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test-utils";
import AdminReportsPage from "../AdminReportsPage";

vi.mock("@/contexts/AdminClinicContext", () => ({
  useAdminClinic: () => ({ currentClinicId: "clinic-1" }),
}));

vi.mock("@/hooks/useAdminReports", () => ({
  useOwnerDashboard: () => ({ data: null, isLoading: false }),
  useAdminReportsDashboard: () => ({ data: null, isLoading: false, isError: false, error: null }),
  useAdminReportsNoShow: () => ({ data: null, isLoading: false, isError: false, error: null }),
  useAdminReportsRevenue: () => ({ data: null, isLoading: false, isError: false, error: null }),
}));

const mockUseMarketingAttributionSummary = vi.fn();

vi.mock("@/hooks/useMarketingAttribution", () => ({
  useMarketingAttributionSummary: (...args: any[]) => mockUseMarketingAttributionSummary(...args),
  useMarketingInsights: () => ({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
  }),
  useMarketingAttributionDrillDown: () => ({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
  }),
  useMarketingCampaigns: () => ({
    data: [
      {
        id: "cmp-1",
        clinic_id: "clinic-1",
        traffic_source_id: null,
        code: "CAMP1",
        name: "Кампания 1",
        external_id: null,
        budget_planned: "1000.00",
        budget_actual: null,
        is_active: true,
      },
    ],
  }),
}));

describe("AdminReportsPage marketing attribution filters", () => {
  beforeEach(() => {
    mockUseMarketingAttributionSummary.mockReturnValue({
      data: {
        clinic_id: "clinic-1",
        date_from: "2026-01-01",
        date_to: "2026-01-07",
        items: [
          {
            traffic_source_code: "google",
            traffic_source_name: "Google Ads",
            campaign_code: "CAMP1",
            campaign_name: "Кампания 1",
            leads_count: 5,
            bookings_count: 3,
            completed_bookings_count: 2,
            unique_patients_count: 2,
            revenue_sum: "10000.00",
            avg_check: "5000.00",
            ad_spend: "1000.00",
            roi: 10,
          },
        ],
      },
      isLoading: false,
      isError: false,
      error: null,
    });
  });

  it("renders marketing attribution table and filter controls", () => {
    renderWithProviders(<AdminReportsPage />);

    expect(screen.getByText(/Marketing and attribution/)).toBeInTheDocument();
    expect(screen.getAllByText("Traffic source").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Campaign").length).toBeGreaterThan(0);

    expect(screen.getAllByText("Кампания 1").length).toBeGreaterThan(0);
    expect(screen.getByText("Google Ads")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("updates attribution query hook when filters change", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AdminReportsPage />);

    await user.click(screen.getAllByLabelText("Traffic source")[0]);
    await user.click(await screen.findByRole("option", { name: /Google Ads/i }));

    await user.click(screen.getAllByLabelText("Campaign")[0]);
    await user.click(await screen.findByRole("option", { name: /Кампания 1/i }));

    await waitFor(() => {
      const lastCallArgs = mockUseMarketingAttributionSummary.mock.calls.at(-1);
      expect(lastCallArgs?.[0]).toBe("clinic-1");
      expect(lastCallArgs?.[3]).toBe("google");
      expect(lastCallArgs?.[4]).toBe("cmp-1");
    });
  });
});

