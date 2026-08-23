import type { ReactElement, ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { renderWithI18n } from "@/i18n/testUtils";
import { ROUTE_PATHS } from "@/routePaths";
import PlatformOwnerInviteAcceptPage from "../PlatformOwnerInviteAcceptPage";

function wrap(ui: ReactNode, initial = "/signup/owner-invite"): ReactElement {
  return (
    <MantineProvider>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route path={ROUTE_PATHS.marketing.ownerInviteAccept} element={ui} />
        </Routes>
      </MemoryRouter>
    </MantineProvider>
  );
}

describe("PlatformOwnerInviteAcceptPage", () => {
  it("renders EN chrome and missing-token alert without a token", async () => {
    await renderWithI18n(wrap(<PlatformOwnerInviteAcceptPage />), { locale: "en" });
    expect(screen.getByRole("heading", { name: /Owner invitation/i })).toBeTruthy();
    expect(screen.getByText(/This link is incomplete/i)).toBeTruthy();
    expect(screen.getByLabelText("Language")).toBeTruthy();
  });
});
