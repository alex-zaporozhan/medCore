/** Экспорт справочника RBAC в CSV (UTF-8 с BOM — корректно открывается в Excel). */

function escapeCsvCell(v: string): string {
  return `"${String(v).replace(/"/g, '""')}"`;
}

export function downloadUtf8Csv(filename: string, rows: string[][]): void {
  const BOM = "\uFEFF";
  const body = rows.map((r) => r.map(escapeCsvCell).join(",")).join("\r\n");
  const blob = new Blob([BOM + body], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  a.click();
  URL.revokeObjectURL(url);
}
