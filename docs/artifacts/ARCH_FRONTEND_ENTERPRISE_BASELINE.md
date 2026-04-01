# Базовая планка прод / enterprise для фронтенда и HTTP-моста

> **Аудитория:** ARCH, QA_ARCH, DEV · **Область:** `frontend/`, единый клиент `frontend/src/api/client.ts`, маршрутизация и guard’ы.  
> **Вне scope:** горизонтальное масштабирование API, БД, очередей, DR, SLO бэкенда — дорожная карта `docs/artifacts/85 plus/QA_ARCH_85_PLUS_8W_EXECUTION_TRACKER.md`.

---

## 1) Уровень зрелости (честная оценка)

| Слой | Состояние | Комментарий |
|------|-----------|-------------|
| Маршруты и зоны | **Сильно** | Канон `routePaths.ts` + сегменты + паритет в тестах; дерево в `App.tsx` привязано к сегментам. |
| Guard’ы `/admin` / `/app` | **Сильно** | `AdminAuthGuard`, `PatientAuthProvider` + `AppLayout`; сравнение login-path через `routePathUtils` (в т.ч. trailing slash). |
| HTTP-мост | **Сильно** | `API_BASE`, `API_STORAGE_KEYS` (единые ключи с `PatientAuthContext`), `getPatientToken` / админские геттеры, разбор ошибок FastAPI в т.ч. **422 `detail[]`**, `ApiErrorWithCode` (+ `name`, `traceId`), политика **401** пациента (`shouldClearPatientSessionOn401`, в т.ч. `/v1/payments`), `X-Request-Id` на исходящие запросы. Тесты: `frontend/src/api/__tests__/*.test.ts`. |
| Наблюдаемость UI | **Базово** | `ApiErrorWithCode.traceId` из тела ответа; корреляция исходящих запросов с `X-Request-Id` (клиент); полноценный OpenTelemetry в браузере — отдельный эпик (см. 8W Week 5). |
| Масштаб 10k+ одновременных пользователей | **Зависит от инфраструктуры** | Статика/PWA за CDN, API за балансировщиком, пулы БД/Redis — не задача только фронта; фронт не держит сессии на сервере SPA. |

Итог: **фундамент маршрутов и транспорта приведён к enterprise-дисциплине документ ↔ код ↔ тесты**; «швейцарские часы» для всего продукта достигаются вместе с бэкенд-треками из 8W.

**Зафиксировано @QA_ARCH (2026-03):** фазы **0–5** `ARCH_FRONTEND_TECH_PASSPORT_DEV_IMPLEMENTATION_PLAN.md` — поверх базы (фазы **0–4**: маршруты, стек, зоны, API-слой **v1.5.3** / план **v1.6.1**, структура §4 **v1.5.4** / план **v1.6.3**, баррели + `hooksBarrelParity.test.ts`): **фаза 5** — TanStack Query по техпаспорту §5: `frontend/src/queryKeys.ts`, доменные хуки вместо прямого `api` на страницах админки (исключение: `AdminLoginPage`), `useAdminAiSettings` / ключи `adminAi`, CRM-ключи в `useCrmLeads.ts`, guards мутаций attention-feed при отсутствии `clinicId`, регресс ключей `frontend/src/__tests__/queryKeys.test.ts`; план **v1.6.4–v1.6.5**, техпаспорт **v1.5.5–v1.5.6** (§5). См. историю версий в техпаспорте и плане.

---

## 2) Инварианты (не ломать без эпика)

Согласованы с `ARCH_FRONTEND_TECH_PASSPORT_DENTAL_BOOKING.md` §7 и расширены транспортом:

1. Публичные path только через `ROUTE_PATHS` / сегменты; новые маршруты — §2 паспорта + `routePaths.test.ts` в одном merge.
2. Пациентский и админский логин определяются **`isPatientLoginPath` / `isAdminLoginPath`** (`routePathUtils.ts`), не дублировать «сырые» сравнения `pathname`.
3. Все вызовы API через `client.ts` (или тонкие обёртки), не дублировать 401-логику.
4. Исходящие запросы получают **`X-Request-Id`**, если заголовок не передан вызывающим кодом — для трассировки в логах API/прокси.

---

## 3) TanStack Query (глобальные дефолты и слой данных)

Файл: `frontend/src/main.tsx`.

- **queries:** `staleTime: 60s`, `retry: 1` — разумный компромисс для чтения под нагрузкой; тяжёлые списки могут переопределять `staleTime`/`gcTime` в хуках.
- **mutations:** используются дефолты библиотеки (обычно без автоповтора); критичные write-операции не должны полагаться на слепой retry без идемпотентности на бэкенде.
- **Ключи и инвалидация (зафиксировано @QA_ARCH, фаза 5):** `frontend/src/queryKeys.ts` — единая фабрика кортежей для доменов (в т.ч. CRM, задачи админки, AI settings); хуки в `frontend/src/hooks/` не вызывают `api` из JSX типовых CRUD; см. техпаспорт §5.

Детальная политика ретраев для AI/интеграций — зона **Week 2** в 8W-трекере (бэкенд/воркеры). **Per-domain** `staleTime`/`gcTime` и перформанс-эпики — см. `ARCH_FRONTEND_85_PLUS_ALIGNMENT.md` §6–§8.

---

## 4) Безопасность (фронт)

- Токены в `localStorage` — осознанный компромисс; снижение риска XSS: санитизация вывода, дисциплина зависимостей, заголовки на стороне CDN/ingress (CSP и др.) — см. `ROLE_FRONTEND`, Week 7 в 8W.
- Не логировать токены и PII в консоль в прод-сборках.

---

## 5) Связанные документы

- Браузерный E2E (enterprise-канон, ADR-006, workflow): `docs/artifacts/ARCH_QA_BROWSER_E2E_ENTERPRISE.md` · `docs/artifacts/ARCH_QA_BROWSER_E2E_OPERATING_INSTRUCTIONS.md` · `docs/adr/ADR-006-playwright-browser-e2e.md` · `.github/workflows/e2e.yml`
- Визуальная унификация + PAW + уровни E2E: `docs/artifacts/ARCH_FRONTEND_VISUAL_UNIFICATION_AND_E2E_ROADMAP.md`
- Техпаспорт фронта: `docs/artifacts/ARCH_FRONTEND_TECH_PASSPORT_DENTAL_BOOKING.md`
- План фаз: `docs/artifacts/ARCH_FRONTEND_TECH_PASSPORT_DEV_IMPLEMENTATION_PLAN.md`
- NFR и UI-состояния: `docs/ARCHITECTURE_EXCELLENCE_PASSPORT.md` §11
- 8 недель 8.5+: трекер (§8 выжимка и полный текст) — `docs/artifacts/85 plus/QA_ARCH_85_PLUS_8W_EXECUTION_TRACKER.md`
- Выравнивание фронта с программой 8W (отложенные эпики, `X-Request-Id` на бэкенде): `docs/artifacts/ARCH_FRONTEND_85_PLUS_ALIGNMENT.md`
- **Визуальный канон админки (2026-03+):** Swiss Slate / Ink — `docs/artifacts/85 plus/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §3.6; не полагаться только на устаревшие упоминания «indigo» в roadmap без ссылки на §3.6.

---

*Версия документа: 1.7 · ссылка на `ARCH_FRONTEND_VISUAL_UNIFICATION_AND_E2E_ROADMAP.md` (PAW, **brand/ink**/Inter, уровни E2E); зафиксировано закрытие фаз **0–5** техплана (TanStack Query §5, `queryKeys`, доработки @QA_ARCH v1.6.5), плюс база **0–4** (§4 баррели + CI-паритет), усиление HTTP-моста v1.5.3 (@QA_ARCH 2026-03); ссылка на `ARCH_FRONTEND_85_PLUS_ALIGNMENT.md`.*
