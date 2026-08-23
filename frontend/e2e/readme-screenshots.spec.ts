import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

/**
 * Optional README captures. Skipped unless README_SCREENSHOTS=1.
 *
 * Compose (nginx UI on :3010, API proxied):
 *   README_SCREENSHOTS=1 BASE_URL=http://127.0.0.1:3010
 *   npx playwright test e2e/readme-screenshots.spec.ts
 *
 * Host Vite preview (:4173) + API on :8000: set README_SCREENSHOTS=1 only
 * (preview webServer stays on). Needs a seeded staff user.
 */
const enabled = process.env.README_SCREENSHOTS === "1";
const email = process.env.README_DEMO_EMAIL ?? "owner.kazan@showcase-mt.demo";
const password = process.env.README_DEMO_PASSWORD ?? "ShowcaseMT2026!";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.resolve(__dirname, "../../docs/public/screenshots");

test.describe("readme screenshots", () => {
  test.describe.configure({ mode: "serial" });
  test.skip(!enabled, "Set README_SCREENSHOTS=1 to capture docs/public/screenshots");

  test("staff login, dashboard, schedule, omni, tasks", async ({ page }) => {
    test.setTimeout(120_000);
    fs.mkdirSync(outDir, { recursive: true });
    await page.setViewportSize({ width: 1440, height: 900 });

    await page.goto("/admin/login");
    await expect(page.getByRole("heading", { name: /clinic staff sign-in/i })).toBeVisible({
      timeout: 15_000,
    });
    await page.screenshot({
      path: path.join(outDir, "admin-login.png"),
      animations: "disabled",
    });

    await page.getByRole("textbox", { name: /email/i }).fill(email);
    await page.getByLabel(/^password$/i).fill(password);
    await page.getByRole("button", { name: /sign in/i }).click();
    // `/admin/login` must not count as a successful landing (`/admin` + `/` matches login).
    await expect(page).toHaveURL(/\/admin\/?$/, { timeout: 20_000 });

    await page.screenshot({
      path: path.join(outDir, "admin-dashboard.png"),
      animations: "disabled",
    });

    await page.goto("/admin/schedule");
    await expect(page.getByRole("heading", { name: /^schedule$/i }).first()).toBeVisible({
      timeout: 15_000,
    });
    await page.screenshot({
      path: path.join(outDir, "admin-schedule.png"),
      animations: "disabled",
    });

    await page.goto("/admin/omni-chat");
    try {
      await expect(page.getByRole("heading", { name: /omni-chat/i }).first()).toBeVisible({
        timeout: 12_000,
      });
    } catch {
      // Seed may not include inbox rows; still capture the chrome.
    }
    await page.screenshot({
      path: path.join(outDir, "admin-omni-chat.png"),
      animations: "disabled",
    });

    await page.goto("/admin/tasks");
    try {
      await expect(page.getByRole("heading", { name: /^tasks/i }).first()).toBeVisible({
        timeout: 12_000,
      });
    } catch {
      // Same: capture whatever the shell rendered.
    }
    await page.screenshot({
      path: path.join(outDir, "admin-tasks.png"),
      animations: "disabled",
    });
  });
});
