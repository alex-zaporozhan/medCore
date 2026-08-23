import type { ReactElement, ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter } from "react-router-dom";
import { renderWithI18n } from "@/i18n/testUtils";
import { ROUTE_PATHS } from "@/routePaths";
import MarketingLandingPage from "../MarketingLandingPage";

function wrap(ui: ReactNode): ReactElement {
  return (
    <MantineProvider>
      <MemoryRouter>{ui}</MemoryRouter>
    </MantineProvider>
  );
}

describe("MarketingLandingPage staff CTA", () => {
  it("sends header Sign in to /admin/login, patient entry stays /login", async () => {
    await renderWithI18n(wrap(<MarketingLandingPage />), { locale: "en" });
    const staff = screen.getByTestId("landing-staff-sign-in");
    expect(staff.getAttribute("href")).toBe(ROUTE_PATHS.admin.login);
    expect(staff.textContent).toMatch(/Sign in/i);
    const patient = screen.getByRole("link", { name: /Patient app/i });
    expect(patient.getAttribute("href")).toBe(ROUTE_PATHS.other.login);
    expect(screen.getByRole("heading", { name: /The operating system for growing your business/i })).toBeTruthy();
    expect(screen.getByLabelText("Language")).toBeTruthy();
  });
});
