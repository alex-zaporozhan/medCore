import { test, expect, type Page } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

/**
 * Optional README captures. Skipped unless README_SCREENSHOTS=1.
 *
 * Compose (nginx UI on :3010, API proxied):
 *   README_SCREENSHOTS=1 BASE_URL=http://127.0.0.1:3010
 *   npx playwright test e2e/readme-screenshots.spec.ts
 */
const enabled = process.env.README_SCREENSHOTS === "1";
const email = process.env.README_DEMO_EMAIL ?? "owner.kazan@showcase-mt.demo";
const password = process.env.README_DEMO_PASSWORD ?? "ShowcaseMT2026!";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.resolve(__dirname, "../../docs/public/screenshots");

async function shot(page: Page, name: string) {
  await page.screenshot({
    path: path.join(outDir, name),
    animations: "disabled",
  });
}

async function waitShell(page: Page) {
  await expect(page.getByText(/loading clinics/i)).toHaveCount(0, { timeout: 25_000 });
}

async function pickDoctors(page: Page, max = 3) {
  const field = page.getByPlaceholder(/select one or more doctors/i).or(page.getByLabel(/^doctors$/i));
  if (!(await field.isVisible().catch(() => false))) return;
  await field.click();
  const options = page.getByRole("option");
  const n = Math.min(max, await options.count());
  for (let i = 0; i < n; i += 1) {
    await options.nth(i).click();
  }
  await page.keyboard.press("Escape");
  await page.waitForTimeout(1_200);
}

test.describe("readme screenshots", () => {
  test.describe.configure({ mode: "serial" });
  test.skip(!enabled, "Set README_SCREENSHOTS=1 to capture docs/public/screenshots");

  test("staff surfaces for README", async ({ page }) => {
    test.setTimeout(180_000);
    fs.mkdirSync(outDir, { recursive: true });
    await page.setViewportSize({ width: 1440, height: 900 });

    await page.goto("/admin/login");
    await expect(page.getByRole("heading", { name: /clinic staff sign-in/i })).toBeVisible({
      timeout: 15_000,
    });
    await page.getByRole("textbox", { name: /^email/i }).fill(email);
    await page.getByRole("textbox", { name: /^password/i }).fill(password);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/admin\/?$/, { timeout: 20_000 });
    await waitShell(page);

    await page.goto("/admin/schedule");
    await expect(page.getByRole("heading", { name: /^schedule$/i }).first()).toBeVisible({
      timeout: 15_000,
    });
    await waitShell(page);
    const gridReady = page.getByText(/^free$/i).or(page.getByText(/in appointment|confirmed|registered/i));
    if (!(await gridReady.first().isVisible({ timeout: 8_000 }).catch(() => false))) {
      await pickDoctors(page, 3);
    }
    await expect(gridReady.first()).toBeVisible({ timeout: 20_000 });
    await page.waitForTimeout(500);
    await shot(page, "admin-schedule.png");

    await page.getByText(/^free$/i).first().click();
    await expect(page.getByRole("heading", { name: /new booking/i })).toBeVisible({
      timeout: 8_000,
    });
    await page.waitForTimeout(400);
    await shot(page, "admin-schedule-booking.png");
    await page.keyboard.press("Escape");
    await expect(page.getByRole("heading", { name: /new booking/i })).toHaveCount(0, {
      timeout: 5_000,
    });

    await page.getByText(/in appointment|confirmed|registered/i).first().click();
    await page.waitForTimeout(700);
    await shot(page, "admin-schedule-visit.png");
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);

    await page.goto("/admin/omni-chat");
    await waitShell(page);
    const inboxRow = page.getByText(/open|closed/i).first();
    if (await inboxRow.isVisible({ timeout: 8_000 }).catch(() => false)) {
      await inboxRow.click();
      await expect(page.getByText(/select a conversation/i)).toHaveCount(0, {
        timeout: 12_000,
      });
      await page.waitForTimeout(800);
    }
    await shot(page, "admin-omni-chat.png");

    await page.goto("/admin/patients");
    await expect(page.getByRole("heading", { name: /^patients$/i }).first()).toBeVisible({
      timeout: 15_000,
    });
    await waitShell(page);
    await page.getByRole("button", { name: "Actions" }).first().click();
    await page.getByRole("menuitem", { name: /open card/i }).click();
    await expect(page.getByRole("tab", { name: "Overview" })).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(400);
    await shot(page, "admin-patient-chart.png");
    await page.keyboard.press("Escape");

    await page.goto("/admin/tasks");
    await expect(page.getByRole("heading", { name: /^tasks/i }).first()).toBeVisible({
      timeout: 15_000,
    });
    await waitShell(page);
    await page.waitForTimeout(1_200);
    await shot(page, "admin-tasks.png");

    await page.goto("/admin/staff-chat");
    await expect(page.getByRole("heading", { name: /team chat/i }).first()).toBeVisible({
      timeout: 15_000,
    });
    await waitShell(page);
    const firstRoom = page.locator("div[class*='mantine-Card-root']").nth(1);
    if (await firstRoom.isVisible().catch(() => false)) {
      await firstRoom.click();
      await page.waitForTimeout(800);
    }
    await shot(page, "admin-staff-chat.png");

    await page.getByRole("button", { name: /new group/i }).first().click();
    await expect(page.getByRole("heading", { name: /new group/i })).toBeVisible({ timeout: 8_000 });
    const members = page.getByPlaceholder(/select staff|members|staff/i).or(page.getByLabel(/members/i));
    if (await members.first().isVisible().catch(() => false)) {
      await members.first().click();
      const opts = page.getByRole("option");
      const n = Math.min(2, await opts.count());
      for (let i = 0; i < n; i += 1) {
        await opts.nth(i).click();
      }
    }
    await page.waitForTimeout(400);
    await shot(page, "admin-staff-chat-group.png");
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);

    await page.goto("/admin/calendar");
    await expect(page.getByRole("heading", { name: /^calendar$/i }).first()).toBeVisible({
      timeout: 15_000,
    });
    await waitShell(page);
    await expect(page.getByRole("button", { name: /new event/i })).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(600);
    await shot(page, "admin-calendar.png");

    await page.getByRole("button", { name: /new event/i }).click();
    await expect(page.getByRole("heading", { name: /new event/i })).toBeVisible({ timeout: 8_000 });
    await page.waitForTimeout(400);
    await shot(page, "admin-calendar-event.png");
  });
});
