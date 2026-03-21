import { test, expect } from "@playwright/test";

/**
 * Публичный smoke без бэкенда: статическая выдача Vite preview + лендинг `/`.
 * Сценарии с `/admin`, `/app` и API — отдельные спеки после поднятия стека (см. ADR-006).
 */
test.describe("public shell", () => {
  test("landing renders Business OS hero", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: /Dental Booking Business OS/i }),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: /Приложение пациента/i })).toBeVisible();
  });
});
