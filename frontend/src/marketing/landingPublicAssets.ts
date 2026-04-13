/**
 * Статика из `frontend/public/` с учётом Vite `base` (подпуть деплоя).
 * Скриншоты лендинга: `public/marketing/landing-hero.{webp|png|jpg}`.
 *
 * @param base — переопределение для тестов; по умолчанию `import.meta.env.BASE_URL`.
 */
export function publicUrlFromRoot(path: string, base: string = import.meta.env.BASE_URL): string {
  const normalized = base.endsWith("/") ? base : `${base}/`;
  const trimmed = path.replace(/^\/+/, "");
  return `${normalized}${trimmed}`;
}

/** Порядок важен: первый успешно загрузившийся файл в `public/marketing/` побеждает. */
export const LANDING_HERO_PUBLIC_URLS: readonly string[] = [
  publicUrlFromRoot("marketing/landing-hero.webp"),
  publicUrlFromRoot("marketing/landing-hero.png"),
  publicUrlFromRoot("marketing/landing-hero.jpg"),
];
