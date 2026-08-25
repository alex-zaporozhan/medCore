import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, screen, within } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { renderWithI18n } from "@/i18n/testUtils";
import { PatientEntityDrawer } from "../PatientEntityDrawer";

const patient = {
  id: "11111111-1111-1111-1111-111111111111",
  phone: "+79001234567",
  full_name: "Jane Doe",
  email: "jane@example.com",
};

vi.mock("@/hooks", () => ({
  useAdminBookings: () => ({ data: [], isLoading: false, isError: false }),
  useAdminLoyaltySummaryByContact: () => ({ data: null, isLoading: false }),
  useAddFamilyMember: () => ({ mutate: vi.fn(), isPending: false }),
  useAdminPatientDiagnoses: () => ({ data: [], isLoading: false }),
  useAdminPatientMedicalFiles: () => ({ data: [], isLoading: false }),
  useAdminPatientMedicalVisits: () => ({ data: [], isLoading: false }),
  useCreateAdminPatientDiagnosis: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateAdminPatientMedicalVisit: () => ({ mutate: vi.fn(), isPending: false }),
  useUploadAdminPatientMedicalFile: () => ({ mutate: vi.fn(), isPending: false }),
  fetchAdminPatientMedicalFileDownloadUrl: vi.fn(),
  useCreatePatient: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdatePatient: () => ({ mutate: vi.fn(), isPending: false }),
  usePatients: () => ({ data: [], isLoading: false }),
  usePatientAiInsight: () => ({ data: null, isLoading: false }),
  useDoctors: () => ({ data: [], isLoading: false }),
}));

vi.mock("@/contexts/AdminClinicContext", () => ({
  useAdminClinic: () => ({ currentClinicId: "clinic-1" }),
}));

async function renderDrawer(viewportWidth = 1280) {
  Object.defineProperty(window, "innerWidth", {
    writable: true,
    configurable: true,
    value: viewportWidth,
  });
  window.dispatchEvent(new Event("resize"));

  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return renderWithI18n(
    <QueryClientProvider client={client}>
      <MantineProvider>
        <MemoryRouter>
          <PatientEntityDrawer
            opened
            onClose={() => {}}
            patient={patient as never}
            mode="view"
            presentation="modal"
          />
        </MemoryRouter>
      </MantineProvider>
    </QueryClientProvider>,
    { locale: "en" },
  );
}

function modalContentEl(): HTMLElement {
  const dialog = screen.getByRole("dialog");
  const content =
    dialog.querySelector(".mantine-Modal-content") ??
    dialog.querySelector('[class*="Modal-content"]') ??
    dialog;
  return content as HTMLElement;
}

function tabsListEl(): HTMLElement {
  const dialog = screen.getByRole("dialog");
  const list = dialog.querySelector('[role="tablist"]');
  if (!list) throw new Error("tablist not found");
  return list as HTMLElement;
}

describe("PatientEntityDrawer geometry (D3)", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "ResizeObserver",
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      },
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps modal shell minHeight stable between Overview and Chart tabs", async () => {
    await renderDrawer(1280);
    const mainMinH = modalContentEl().style.minHeight;

    fireEvent.click(screen.getByRole("tab", { name: /overview/i }));
    const overviewMinH = modalContentEl().style.minHeight;

    fireEvent.click(screen.getByRole("tab", { name: /chart \/ notes/i }));
    const notesMinH = modalContentEl().style.minHeight;

    expect(mainMinH).toBe("560px");
    expect(overviewMinH).toBe("560px");
    expect(notesMinH).toBe("560px");
  });

  it("uses single-line tab row with horizontal scroll at 360px", async () => {
    await renderDrawer(360);
    const list = tabsListEl();
    const style = window.getComputedStyle(list);
    expect(style.flexWrap).toBe("nowrap");
    expect(list.scrollHeight).toBeLessThanOrEqual(48);
    const tabs = within(list).getAllByRole("tab");
    expect(tabs.length).toBe(6);
  });

  it("renders six tab panels with ScrollArea (fixed PATIENT_MODAL_TABS_H)", async () => {
    await renderDrawer(1280);
    const dialog = screen.getByRole("dialog");
    const scrollRoots = dialog.querySelectorAll(".mantine-ScrollArea-root");
    expect(scrollRoots.length).toBeGreaterThanOrEqual(6);
  });
});
