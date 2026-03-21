import { readdirSync, readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const hooksDir = join(dirname(fileURLToPath(import.meta.url)), "..");

/**
 * Каждый файл `hooks/use*.ts` должен быть подключён в `hooks/index.ts` (техпаспорт §4.1).
 * Иначе `@/hooks` не отражает полный доменный слой — риск дрейфа при новых фичах.
 */
function listUseHookModules(): string[] {
  return readdirSync(hooksDir)
    .filter((f) => f.startsWith("use") && f.endsWith(".ts"))
    .map((f) => f.replace(/\.ts$/, ""));
}

describe("hooks barrel parity", () => {
  it("index.ts imports every use*.ts module", () => {
    const indexPath = join(hooksDir, "index.ts");
    const index = readFileSync(indexPath, "utf8");
    for (const mod of listUseHookModules()) {
      const fromDouble = `from "./${mod}"`;
      const fromSingle = `from './${mod}'`;
      expect(
        index.includes(fromDouble) || index.includes(fromSingle),
        `hooks/index.ts must import "./${mod}" (barrel incomplete)`
      ).toBe(true);
    }
  });
});
