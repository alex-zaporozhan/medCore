import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { renderWithI18n } from "@/i18n/testUtils";
import { ClinicSelector } from "../ClinicSelector";

vi.mock("@/contexts/AdminClinicContext", () => ({
  useAdminClinic: () => ({
    selectableClinics: [],
    currentClinicId: null,
    setCurrentClinicId: vi.fn(),
    isClinicScopeLocked: false,
    isLoading: true,
  }),
}));

describe("ClinicSelector A1", () => {
  it("shows EN loading chrome", async () => {
    await renderWithI18n(
      <MantineProvider>
        <ClinicSelector />
      </MantineProvider>,
      { locale: "en" },
    );
    expect(screen.getByText("Loading clinics…")).toBeTruthy();
  });
});
