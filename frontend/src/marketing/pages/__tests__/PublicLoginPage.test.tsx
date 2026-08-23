import type { ReactElement, ReactNode } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import i18n, { UI_LOCALE_STORAGE_KEY } from "@/i18n";
import { renderWithI18n } from "@/i18n/testUtils";
import PublicLoginPage from "../PublicLoginPage";

function wrap(ui: ReactNode): ReactElement {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return (
    <MantineProvider>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{ui}</MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>
  );
}

describe("PublicLoginPage", () => {
  afterEach(async () => {
    localStorage.removeItem(UI_LOCALE_STORAGE_KEY);
    await i18n.changeLanguage("en");
  });

  it("renders EN public hub chrome by default", async () => {
    await renderWithI18n(wrap(<PublicLoginPage />), { locale: "en" });
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Clinic: staff and owner" })).toBeTruthy();
    expect(screen.getByText("Patients")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: /^Вход$/ })).toBeNull();
  });

  it("renders RU public hub chrome when locale is ru", async () => {
    await renderWithI18n(wrap(<PublicLoginPage />), { locale: "ru" });
    expect(screen.getByRole("heading", { name: "Вход" })).toBeTruthy();
    expect(screen.getByText("Пациентам")).toBeTruthy();
  });
});
