# Фаза 8 — приёмка «покупатель / техлид» (критерии D1–D3)

> **Версия:** 2026-04-09  
> **Мастер-план:** [`MASTER_FRONTEND_EXECUTION_PLAN.md`](./MASTER_FRONTEND_EXECUTION_PLAN.md) · **критерии:** [`pages/MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md`](./pages/MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md) (D)

## Пояснение: что обязан сделать лид (фазы 6–8 одной страницей)

| Фаза | Что уже может быть сделано без вас | Что без вас не получится |
|------|-----------------------------------|---------------------------|
| **6 (C4)** | Команды `verify`, `npm run build`, тест `adminNoRawMantineDrawer` — см. журнал в [`PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md`](./PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md). | Осмотр пилотных экранов в браузере и запись замечаний (шаблон там же). |
| **7 (C5)** | Матрица сценариев и ссылки на паспорта подготовлены в [`PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md`](./PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md). | Прогон сценариев «как пользователь» и правка колонок **Статус / Gap** по факту. |
| **8 (D1–D3)** | Чеклисты и ссылки на регламенты — в этом файле ниже. | Проставить галочки/вердикт **A → B → C** по рубрике, согласовать с безопасностью и выпустить **подпись** (тикет, email, протокол — не обязательно git). |

**Итог:** документация снимает вопрос «что проверять»; вы даёте **доказательство**, что это проверено в нужной среде, и принимаете решение.

## Назначение

Структурировать **D1–D3** в виде чеклиста для человека (лид / владелец продукта / техлид). **Подпись приёмки** и юридическое «go-live» этим файлом **не заменяются** — только подготовка доказательной базы и ссылок.

## D1 — Логика сценариев и состояния UI

| # | Проверка | Источник истины / как закрыть |
|---|----------|-------------------------------|
| D1.1 | Ключевые сценарии без логических дыр | Матрица [`PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md`](./PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md); паспорта с gap scan |
| D1.2 | Loading осмысленен (skeleton/spinner), не «вечная» загрузка без ошибки | Код страниц + рубрика μ3 в [`../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md`](../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md) |
| D1.3 | Empty state с подсказкой действия | [`../COPY_STYLE_POLICY_RU.md`](../COPY_STYLE_POLICY_RU.md); DOMAIN_STANDARDS в [`../DOMAIN_STANDARDS.md`](../DOMAIN_STANDARDS.md) |
| D1.4 | Ошибки API — коротко, по-русски, без traceback в prod | `frontend/src/api/client.ts` (`normalizeErrorMessage`); паспорта «Логика и данные» |

## D2 — Безопасность периметра и данных

| # | Проверка | Источник истины / как закрыть |
|---|----------|-------------------------------|
| D2.1 | RBAC и тенантность на бэкенде для админских `/v1/admin/...` | `require_permissions`, `clinic_id` в контексте; [`../product_state/BACKEND_PASSPORT.md`](../product_state/BACKEND_PASSPORT.md) |
| D2.2 | Разделение контуров (пациент / админ / platform founder) | JWT claims и роутинг — см. архитектурный индекс [`../architecture/INDEX.md`](../architecture/INDEX.md) |
| D2.3 | Секреты и webhooks | `.env.example`, runbooks операций в `docs/operations/` |
| D2.4 | Зависимости и CI | `Jenkinsfile`, [`../../CI_CD.md`](../../CI_CD.md), workflow в `.github/workflows/` (дополнение к Jenkins) |

*Паспорт одной страницы не заменяет этот блок: D2 — уровень системы.*

## D3 — Итерации рубрики Enterprise SaaS (UI)

Рубрика и итерации **A / B / C** описаны в [`../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md`](../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md) §7.

| Итерация | Выход (артефакт) | Когда считать шаг сделанным |
|----------|------------------|----------------------------|
| **A — Discovery** | Таблица маршрут ↔ API; список P0 «нет запросов» | Документ или раздел в PR; обновление паспортов фактами |
| **B — Strict** | Оценки по микро-осям 0/1/2 для выборки экранов | Запись в тикете / отчёте QA |
| **C — Buyer simulation** | Вердикт go / no-go по макро-осям | Протокол встречи или подписанный short report лида |

Между итерациями: обновлять [`pages/`](./pages/) без дублирования полного чеклиста в каждом файле (см. тот же §7).

## Сводная трассировка на артефакты фаз 0–7

| Фаза плана | Артефакт закрытия |
|------------|-------------------|
| 0 | `verify` |
| 1–3 | RAG + канон + трекер Z1–Z6 |
| 4–5 | C1–C3 (код + копирайт) |
| 6 | [`PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md`](./PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md) |
| 7 | [`PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md`](./PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md) |
| 8 | Этот чеклист + **человеческая** подпись |

## Шаблон строки подписи (вне репозитория или в тикете)

```text
Приёмка D1–D3 по релизу ______: выполнено / с оговорками.
Ответственный: ______ Дата: ______
Оговорки: ______
```
