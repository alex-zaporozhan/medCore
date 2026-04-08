import { defineConfig, devices } from "@playwright/test";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Локально: `npm run build`, затем `npm run test:e2e` (поднимет preview).
 * CI: см. `.github/workflows/e2e.yml` — build перед тестом.
 * Полный контур с API/логином — см. workflow e2e в .github/workflows и docker-compose.
 */
export default defineConfig({
  testDir: path.join(__dirname, "e2e"),
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI ? "github" : [["html", { open: "never" }]],
  use: {
    baseURL: process.env.BASE_URL ?? "http://127.0.0.1:4173",
    trace: "on-first-retry",
    serviceWorkers: "block",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: process.env.E2E_EXTERNAL_BASE_URL
    ? undefined
    : {
        command: "npm run preview -- --host 127.0.0.1 --port 4173",
        cwd: __dirname,
        url: "http://127.0.0.1:4173",
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
