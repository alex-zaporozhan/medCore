# Согласование ключей entitlement — Phase 0

> **Цель Фазы 0 (МП):** список ключей **не противоречит** [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md) **§4**, **§13.1**, **§16.5**, **§24** и будущему `require_entitlement` / `organization_entitlements`.  
> **Не заменяет** [ENTITLEMENT_ROUTER_INVENTORY.md](./ENTITLEMENT_ROUTER_INVENTORY.md) (обязателен до merge Фазы 1c).

## Канонический набор ключей (§4 + §16.5)

| Ключ | §4 | §16.5 | Примечание |
|------|-----|-------|------------|
| `core.base` | да | да | Базовый пакет §13.1; в каталоге как неотделяемая база без отдельной продажи без политики |
| `omni.embed.bundle` | да | да | Моно-пакет embed + PWA + каналы + Битрикс + см. §24 |
| `ai.assistant.chat` | да | да | §24.2 |
| `ai.rag.org_kb` | да | да | §24.3, изоляция per org |
| `crm.pipeline` | да | да | |
| `retention.bundle` | да | да | |
| `tasks.kanban` | да | да | |
| `marketing.attribution` | да | да | |
| `omni.extended` | да | — (в §16.5 как смысл в §4) | Расширенный omnichannel |
| `network.multi_clinic` | да | — | Вторая+ локация |
| `import.crm_v1` | да | — | ADR-010 |
| `import.enterprise_migrator` | да | — | §25, позже |
| `commerce.store_network` | да | — | §26, поздняя опция |
| `erp.reporting_plus` | да | — | Если выделено в продукте |

## Согласованность с §24 (пресет РФ)

Пресет «Чат + PWA + omnichannel + Битрикс24» в мастер-плане выражается **набором ключей §4**, чаще всего **`omni.embed.bundle`** и при необходимости надстройками **`ai.*`** — без изобретения новых имён в сидере без правки этой таблицы и МП §4.

## Факт кода на Phase 0

CRM и retention завязаны на **`EDITION`**; задачи и маркетинг — **без** того же класса gate в роутерах (МП §12.1). Это **не** противоречие таблице выше до Фазы **1c**, если инвентарь роутеров и LEAD приняли явные строки для `admin_tasks`, `admin_marketing`, `admin_marketing_attribution`.

**Актуализация (Phase 1e, 2026-04-06):** в БД-каталоге (`platform_catalog_options`, миграция `20260412_phase1e_embed_catalog_and_keys`) присутствуют строки для **`omni.embed.bundle`**, **`ai.assistant.chat`**, **`ai.rag.org_kb`**, **`marketing.attribution`**, **`retention.bundle`** — согласовано с таблицей канонических ключей выше и гейтами `require_entitlement` / публичным embed.

## История

- **2026-04-05** — выгрузка Phase 0 для трассировки §4 / §16.5 / §24.
- **2026-04-05 (QA_ARCH)** — отмечено: таблица **не** заменяет явную вычитку LEAD на расхождения с будущим сидером/конструктором; перед 1b/1c сверить ключи с живым каталогом в коде.
