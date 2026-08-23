import { test, expect } from "@playwright/test";

/**
 * Публичный smoke без бэкенда: статическая выдача Vite preview + лендинг `/`.
 * Сценарии с `/admin`, `/app` и API — отдельные спеки после поднятия стека (см. ADR-006).
 */
test.describe("public shell", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("ui.locale", "en");
    });
  });

  test("landing renders SaaS hero and patient app link", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: /The operating system for growing your business/i }),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: /Patient app/i })).toBeVisible();
    const hero = page.locator(".marketing-hero-shot");
    await expect(hero).toBeVisible();
    await expect
      .poll(() => hero.evaluate((el: HTMLImageElement) => el.naturalWidth))
      .toBeGreaterThan(0);
  });
});
