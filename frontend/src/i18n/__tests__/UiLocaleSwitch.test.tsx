import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { renderWithI18n } from "../testUtils";
import { UiLocaleSwitch } from "../UiLocaleSwitch";

describe("UiLocaleSwitch", () => {
  it("renders EN/RU segments with language aria-label", async () => {
    await renderWithI18n(
      <MantineProvider>
        <UiLocaleSwitch />
      </MantineProvider>,
    );
    expect(screen.getByLabelText("Language")).toBeTruthy();
    expect(screen.getByText("EN")).toBeTruthy();
    expect(screen.getByText("RU")).toBeTruthy();
  });
});
