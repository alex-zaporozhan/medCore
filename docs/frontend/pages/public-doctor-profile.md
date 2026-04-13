# Public Doctor Profile

## Метаданные

- **Path:** `/:clinicSlug/doctors/:doctorSlug`
- **Зона:** public (маркетинг / SEO)
- **Компонент(ы) в App.tsx:** `PublicDoctorProfilePage`
- **Файл страницы:** `frontend/src/marketing/pages/PublicDoctorProfilePage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/marketing/pages/PublicDoctorProfilePage.tsx`<br>`frontend/src/routePaths.ts ← импорт из frontend/src/marketing/pages/PublicDoctorProfilePage.tsx` |
| Строк (сумма по фрагментам) | 274 |
| Хуки (эвристика, union) | `usePublicDoctorProfileBySlugs` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Публичная карточка врача по slug клиники и slug врача: ФИО, специализация, фото, краткий текст и блок «О враче»; кнопка перехода на поток онлайн-записи с предзаполненными `clinic_id` и `doctor_id` в query.

## Логика и данные

- **Хуки:** `usePublicDoctorProfileBySlugs` из `@/hooks/usePublicDoctorProfile`; `useParams` для `clinicSlug`, `doctorSlug`.
- **queryKey:** массив `public`, `doctorProfile`, clinicSlug, doctorSlug.
- **API:** `GET /v1/public/clinics/by-slug/{clinicSlug}/doctors/{doctorSlug}` — DTO с полями профиля и идентификаторами для ссылки на запись.

## RBAC / entitlements / edition

- Публичный маршрут без JWT (**fact**). Ограничения только на стороне API (существование slug, публикация профиля).

## UI-скелет (as-built)

`Container` → `Paper`: состояния загрузки текстом, ошибка через `QueryErrorAlert`, успех — `Avatar`, `Title`, кнопка `Link` на `ROUTE_PATHS.patient.booking` с query-параметрами.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer, GlassModal, Modal, Menu:** на странице нет.

## Целевой UX (target vs as-built)

- *target:* рендер Markdown в «О враче», отзывы, расписание слотов на публичной странице.
- *as-built:* поле `about_md` выводится как plain text с `white-space: pre-wrap`, без парсера Markdown.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Нет канонического SEO-мета (title/description) в компоненте.
- Ссылка «Записаться» ведёт на общий booking; нет проверки slug клиники в пути пациентского приложения на этой странице.
