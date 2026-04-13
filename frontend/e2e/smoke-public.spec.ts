import { test, expect } from "@playwright/test";

/**
 * Публичный smoke без бэкенда: статическая выдача Vite preview + лендинг `/`.
 * Сценарии с `/admin`, `/app` и API — отдельные спеки после поднятия стека (см. ADR-006).
 */
test.describe("public shell", () => {
  test("landing renders SaaS hero and patient app link", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: /Операционная система для роста вашего бизнеса/i }),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: /Приложение пациента/i })).toBeVisible();
    const hero = page.locator(".marketing-hero-shot");
    await expect(hero).toBeVisible();
    await expect
      .poll(() => hero.evaluate((el: HTMLImageElement) => el.naturalWidth))
      .toBeGreaterThan(0);
  });
});
