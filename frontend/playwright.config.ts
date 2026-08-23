import { defineConfig, devices } from "@playwright/test";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const useExternalServer =
  Boolean(process.env.E2E_EXTERNAL_BASE_URL) ||
  (process.env.README_SCREENSHOTS === "1" && Boolean(process.env.BASE_URL));

/**
 * Local: `npm run build`, then `npm run test:e2e` (starts Vite preview).
 * Compose UI: set BASE_URL + E2E_EXTERNAL_BASE_URL (or README_SCREENSHOTS=1 + BASE_URL)
 * so Playwright does not also spawn preview on 4173.
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
  webServer: useExternalServer
    ? undefined
    : {
        command: "npm run preview -- --host 127.0.0.1 --port 4173",
        cwd: __dirname,
        url: "http://127.0.0.1:4173",
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
