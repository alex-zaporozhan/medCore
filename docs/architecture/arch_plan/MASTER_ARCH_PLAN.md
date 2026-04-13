# Глобальный архитектурный план исполнения SaaS (сводный документ @ARCH)

> **Назначение:** один файл «сверху вниз»: контекст, фазы, порядок для @DEV, ссылки на детализацию в этой же папке и на [SAAS_STRENGTHENING_MASTER_PLAN.md](../SAAS_STRENGTHENING_MASTER_PLAN.md) (**МП**).

## 1. Контекст и цель

Продуктовая цель МП — **один деплой платформы** с ролью **Основатель** (vendor), **Владельцы** бизнесов, гибкими тарифами, оплатой подписки, провижинингом, модулями по entitlements и наблюдаемостью. Текущий репозиторий по честности МП (**§2b**) — **монолит клиники** + узкий **MVP spine** контура B биллинга; полноценный platform-operator и self-service **не заявлены** до закрытия фаз **1a–1c** и ворот **§19**.

## 2. Как устроена документация исполнения

| Документ | Роль |
|----------|------|
| **MASTER_ARCH_PLAN.md** (этот файл) | Сводка и навигация |
| [README.md](./README.md) | Оглавление папки `arch_plan/` |
| [00_ARCHITECTURAL_LAYERS_AND_PRINCIPLES.md](./00_ARCHITECTURAL_LAYERS_AND_PRINCIPLES.md) | Оси, слои, ворота, §17.1 |
| [DEV_EXECUTION_SEQUENCE.md](./DEV_EXECUTION_SEQUENCE.md) | **С чего начать @DEV**, параллельные P0 |
| [TRACEABILITY_MATRIX.md](./TRACEABILITY_MATRIX.md) | МП § → файлы репозитория |
| [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) | Долг **полного** закрытия фаз сверх DoD (QA_ARCH) |
| [SAAS_EPIC_TRACEABILITY_INDEX.md](../SAAS_EPIC_TRACEABILITY_INDEX.md) | Эпик-срезы LEAD: Epic_ID ↔ МП § ↔ backlog ↔ QA_REPORT; `STREAM_*_EPICS.md` в этой папке |
| `01_` … `10_` | Поэтапная детализация под фазы МП §15 и блоки §25–§31 |

## 3. Фазы (кратко)

| Фаза | Смысл | Детализация |
|------|--------|-------------|
| **0** | ADR, ключи, U-*, go/no-go, §17.1 | [01_PHASE_0_PREPARATION.md](./01_PHASE_0_PREPARATION.md) |
| **1a** | Platform core: JWT Основателя, изоляция, pending в БД | [02_PHASE_1A_PLATFORM_CORE.md](./02_PHASE_1A_PLATFORM_CORE.md) |
| **1b** | Коммерция и UX: каталог, лендинг, кабинет, полный B | [03_PHASE_1B_COMMERCE_AND_UX.md](./03_PHASE_1B_COMMERCE_AND_UX.md) |
| **1c** | Entitlements вместо box-only гейтов | [04_PHASE_1C_ENTITLEMENTS.md](./04_PHASE_1C_ENTITLEMENTS.md) |
| **1d** | Prometheus/Grafana/алерты | [05_PHASE_1D_OBSERVABILITY.md](./05_PHASE_1D_OBSERVABILITY.md) |
| **1e** | Offboarding/export, embed/AI/RAG дорожная карта | [06_PHASE_1E_LIFECYCLE_EMBED.md](./06_PHASE_1E_LIFECYCLE_EMBED.md) |
| **2** | BCP, outbox, CI | [07_PHASE_2_RELIABILITY.md](./07_PHASE_2_RELIABILITY.md) |
| **3+** | Vertical, импорт, enterprise | [08_PHASE_3_PLUS.md](./08_PHASE_3_PLUS.md) |
| **4** | Commerce опционально | [09_PHASE_4_OPTIONAL_COMMERCE.md](./09_PHASE_4_OPTIONAL_COMMERCE.md) |
| **Сквозное** | §27–§31 | [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md) |

Диаграмма зависимостей фаз — в [00_ARCHITECTURAL_LAYERS_AND_PRINCIPLES.md](./00_ARCHITECTURAL_LAYERS_AND_PRINCIPLES.md).

## 4. С чего начинать @DEV (один абзац)

Сначала **фаза 0** и запись **§17.1** при любом плане на **≥2 реплики** API с публичным B/signup. Затем **1a** (границы platform/tenant и JWT), параллельно готовить **1d** если не блокирует релиз. **1b** доводит коммерцию до МП §6/§16.6 (не путать с MVP spine). **1c** — только после приёмки [ENTITLEMENT_ROUTER_INVENTORY.md](../ENTITLEMENT_ROUTER_INVENTORY.md). **1e** и **2** усиливают жизненный цикл и надёжность. **3+** и **4** — после стабилизации ядра. Сквозные §27–§28 вшивать в публичные фичи, а не «в конце».

## 5. Неизменные архитектурные инварианты (из МП)

- Провижининг org из **подтверждённой оплаты** и строки в БД; Redis вспомогательный (§6).
- Webhook **A** и **B** разведены; тесты A **не** закрывают DoD B (§2c, §15b 1b).
- Не расширять `/owner/*` без **U-005**.
- Новые `security_*` / spam / billing метрики — через **реестр** [07_metrics_observability.md](../07_metrics_observability.md) (§11).
- Импорт и массовый commit — **батчи и идемпотентность** (§25.3, §16.6 шаг 0).

## 6. Версия

- **2026-04-05** — первая выкладка сводного плана по МП.
