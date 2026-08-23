import type { ReactElement, ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter } from "react-router-dom";
import { renderWithI18n } from "@/i18n/testUtils";
import MarketingSandboxPage from "../MarketingSandboxPage";

function wrap(ui: ReactNode): ReactElement {
  return (
    <MantineProvider>
      <MemoryRouter>{ui}</MemoryRouter>
    </MantineProvider>
  );
}

describe("MarketingSandboxPage", () => {
  it("renders EN chrome and a locale switcher", async () => {
    await renderWithI18n(wrap(<MarketingSandboxPage />), { locale: "en" });
    expect(
      screen.getByRole("heading", { name: /The demo environment is being prepared/i }),
    ).toBeTruthy();
    expect(screen.getByLabelText("Language")).toBeTruthy();
  });
});
