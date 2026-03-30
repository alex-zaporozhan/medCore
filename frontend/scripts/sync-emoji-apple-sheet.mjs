/**
 * Копирует Apple spritesheet (sheets-256/64.png) из emoji-datasource-apple в public/,
 * чтобы emoji-mart мог отрисовать единый Apple-set без cdn.jsdelivr.net.
 */
import { copyFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(__dirname, "..");
const src = join(
  frontendRoot,
  "node_modules/emoji-datasource-apple/img/apple/sheets-256/64.png"
);
const destDir = join(frontendRoot, "public/emoji-datasource/apple/sheets-256");
const dest = join(destDir, "64.png");

if (!existsSync(src)) {
  globalThis.console.error(
    "[sync-emoji-apple-sheet] Missing source file. Run `npm ci` in frontend/ (emoji-datasource-apple must be installed).\n" +
      `  Expected: ${src}`
  );
  process.exit(1);
}

mkdirSync(destDir, { recursive: true });
copyFileSync(src, dest);
globalThis.console.log(`[sync-emoji-apple-sheet] Copied Apple spritesheet → ${dest}`);
