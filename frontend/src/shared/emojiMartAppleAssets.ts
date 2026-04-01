/** Путь под `public/` после sync-скрипта; Vite отдаёт как статику. */
const APPLE_SHEET = "emoji-datasource/apple/sheets-256/64.png";

export function emojiMartAppleSpritesheetUrl(): string {
  const base = import.meta.env.BASE_URL;
  const normalized = base.endsWith("/") ? base : `${base}/`;
  return `${normalized}${APPLE_SHEET}`;
}
