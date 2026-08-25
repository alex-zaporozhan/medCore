import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const adminRoot = path.resolve(__dirname, "..");

/**
 * Wave A owned files — Q13 grep-gate.
 * Matches GLOBAL AUDIT mechanical gate + Q8 `AdminOmniChatPage`.
 * Scans: quoted literals + bare JSX text nodes (not comments).
 */
const WAVE_A_TSX_FILES = [
  "pages/AdminStaffCalendarPage.tsx",
  "components/entity/PatientEntityDrawer.tsx",
  "components/entity/BookingEntityDrawer.tsx",
  "pages/AdminLeadsLogPage.tsx",
  "pages/AdminStaffChatPage.tsx",
  "pages/AdminSalesPipelinePage.tsx",
  "pages/AdminTasksPage.tsx",
  "pages/AdminOmniChannelsPage.tsx",
  "pages/AdminOmniChatPage.tsx",
] as const;

const CYRILLIC = /[А-Яа-яЁё]/;

/** Strip block and line comments so JSDoc / // do not false-positive. */
function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/[^\n]*/g, "");
}

/** Quoted string literals (single, double, backtick). */
function findQuotedCyrillicLiterals(source: string): string[] {
  const hits: string[] = [];
  const stripped = stripComments(source);
  const re = /(["'`])((?:\\.|(?!\1)[^\\])*)\1/g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(stripped)) !== null) {
    const literal = match[2];
    if (CYRILLIC.test(literal)) {
      hits.push(`quoted:"${literal.slice(0, 60)}"`);
    }
  }
  return hits;
}

/** Bare JSX text like `>Участники<` (excludes `>{expr}<`). */
function findBareJsxCyrillicText(source: string): string[] {
  const hits: string[] = [];
  const stripped = stripComments(source);
  const re = />([^<{][^<\n]*[А-Яа-яЁё][^<\n]*)</g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(stripped)) !== null) {
    const text = match[1].trim();
    if (text) hits.push(`jsx:"${text.slice(0, 60)}"`);
  }
  return hits;
}

function findCyrillicChromeLiterals(source: string): string[] {
  return [...findQuotedCyrillicLiterals(source), ...findBareJsxCyrillicText(source)];
}

describe("wave A Cyrillic grep-gate (Q13)", () => {
  for (const rel of WAVE_A_TSX_FILES) {
    it(`has no Cyrillic in user-facing literals: ${rel}`, () => {
      const abs = path.join(adminRoot, rel);
      const source = readFileSync(abs, "utf8");
      const hits = findCyrillicChromeLiterals(source);
      expect(hits, `Cyrillic in ${rel}: ${hits.join(" | ")}`).toEqual([]);
    });
  }
});
