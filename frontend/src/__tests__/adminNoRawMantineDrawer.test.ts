import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

/** Importing Drawer from @mantine/core in admin UI bypasses AdminDrawer shell (TECH_PASSPORT §6). */
const RAW_DRAWER_IMPORT = /import\s*\{[^}]*\bDrawer\b[^}]*\}\s*from\s*["']@mantine\/core["']/;

function walkTsFiles(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    if (name === "__tests__" || name === "node_modules") continue;
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walkTsFiles(p, out);
    else if (/\.tsx?$/.test(name)) out.push(p);
  }
  return out;
}

describe("admin shell: no raw Mantine Drawer", () => {
  it("frontend/src/admin has no Drawer import from @mantine/core (use AdminDrawer)", () => {
    const adminRoot = join(__dirname, "../admin");
    const files = walkTsFiles(adminRoot);
    const offenders: string[] = [];
    for (const file of files) {
      const src = readFileSync(file, "utf8");
      if (RAW_DRAWER_IMPORT.test(src)) offenders.push(file.replace(/\\/g, "/"));
    }
    expect(
      offenders,
      `Use AdminDrawer from @/shared/ui instead of Drawer from @mantine/core:\n${offenders.join("\n")}`
    ).toEqual([]);
  });
});
