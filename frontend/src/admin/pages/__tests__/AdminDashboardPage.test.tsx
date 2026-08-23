import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { renderWithI18n } from "@/i18n/testUtils";
import AdminDashboardPage from "../AdminDashboardPage";

vi.mock("@/contexts/AdminClinicContext", () => ({
  useAdminClinic: () => ({
    currentClinicId: "clinic-1",
    clinics: [{ id: "clinic-1", name: "Demo Clinic" }],
  }),
}));

vi.mock("@/hooks/useAdminReports", () => ({
  useAdminReportsDashboardByClinics: () => ({
    data: {
      bookings_completed: 0,
      new_patients: 0,
      bookings_cancelled: 0,
      bookings_no_show: 0,
      chat_writers_count: 0,
      empty_slot_hours: "0",
      day_pulse_score: 50,
    },
    isLoading: false,
    isError: false,
    error: null,
  }),
}));

vi.mock("@/hooks/useStaffCollab", () => ({
  useStaffFeedPosts: () => ({ data: [], isLoading: false }),
  useCreateStaffFeedPost: () => ({ mutate: vi.fn(), isPending: false }),
  useToggleStaffFeedPostLike: () => ({ mutate: vi.fn(), isPending: false, variables: undefined }),
  useUpdateStaffFeedPost: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteStaffFeedPost: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useStaffFeedComments: () => ({ data: [], isLoading: false }),
  useAddStaffFeedComment: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUploadStaffFeedCommentAttachment: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateStaffFeedComment: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteStaffFeedComment: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock("@/hooks", () => ({
  useRevenueHunterSaved: () => ({ data: null }),
  isRevenueHunterEnabled: () => false,
  useAdminSession: () => ({
    data: { permissions: ["manage_staff_collab"], roles: ["owner"] },
    isLoading: false,
  }),
  useMyStaffProfile: () => ({ data: { full_name: "Ada Lovelace", avatar_url: null } }),
}));

vi.mock("@/api/client", () => ({
  api: { getBlob: vi.fn(), postFormData: vi.fn() },
  ApiErrorWithCode: class extends Error {},
  getAdminId: () => "admin-1",
}));

describe("AdminDashboardPage feed i18n", () => {
  it("shows EN chrome from feed.json, not Russian literals", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    await renderWithI18n(
      <QueryClientProvider client={client}>
        <MantineProvider>
          <MemoryRouter>
            <AdminDashboardPage />
          </MemoryRouter>
        </MantineProvider>
      </QueryClientProvider>,
      { locale: "en" },
    );
    expect(screen.getByText("Feed")).toBeTruthy();
    expect(screen.getByText("No posts yet")).toBeTruthy();
    expect(screen.getByText("Total visits")).toBeTruthy();
    expect(screen.queryByText("Лента")).toBeNull();
    expect(screen.queryByText("Пока нет постов")).toBeNull();
  });
});
