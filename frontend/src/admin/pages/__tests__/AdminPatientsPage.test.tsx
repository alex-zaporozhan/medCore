import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { renderWithI18n } from "@/i18n/testUtils";
import AdminPatientsPage from "../AdminPatientsPage";

vi.mock("@/contexts/AdminClinicContext", () => ({
  useAdminClinic: () => ({
    currentClinicId: "clinic-1",
    clinics: [{ id: "clinic-1", name: "Demo Clinic" }],
    selectableClinics: [{ id: "clinic-1", name: "Demo Clinic" }],
    setCurrentClinicId: vi.fn(),
    isClinicScopeLocked: false,
    isLoading: false,
  }),
}));

vi.mock("@/admin/components/entity/PatientEntityDrawer", () => ({
  PatientEntityDrawer: () => null,
}));

vi.mock("@/hooks", () => ({
  useAdminSession: () => ({
    data: { permissions: ["patients.pii.read"] },
    isLoading: false,
  }),
  usePatients: () => ({ data: [], isLoading: false, isError: false, error: null }),
  useAdminFormTemplates: () => ({ data: [] }),
  useSendFormLink: () => ({ mutate: vi.fn(), isPending: false }),
  useDeletePatient: () => ({ mutate: vi.fn(), isPending: false }),
}));

describe("AdminPatientsPage A3", () => {
  it("shows EN empty chrome, not Russian literals", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    await renderWithI18n(
      <QueryClientProvider client={client}>
        <MantineProvider>
          <MemoryRouter>
            <AdminPatientsPage />
          </MemoryRouter>
        </MantineProvider>
      </QueryClientProvider>,
      { locale: "en" },
    );
    expect(screen.getByText("Patients")).toBeTruthy();
    expect(screen.getByText("No patients")).toBeTruthy();
    expect(screen.getByText("Add the first patient or change the filters.")).toBeTruthy();
    expect(screen.queryByText("Пациенты")).toBeNull();
  });
});
