# QA_ARCH: срез 1a-E4 — audit чувствительных действий `/platform/*`

**Дата:** 2026-04-06  
**Epic:** 1a-E4  
**Статус:** закрыт (structured log, без лишней PII)

## Реализация

- Модуль `src/core/platform_audit.py` — logger `platform_audit`, поля: `action`, `actor_founder_id`, `resource_type`, `resource_id`, без email.
- Вызовы на мутациях: `platform_internal` (upsert каталога, retry provision, mint owner invite), события входа/TOTP в `platform_founder_auth`.
- Каталог по-прежнему пишет structured event в сервисе (`platform_catalog_plan_upsert`); HTTP-слой дублирует семантику для трассировки запросов Основателя.

## DoD

- [x] Structured log на критичных мутациях platform-internal и контролируемых шагах auth/TOTP.
- [x] Без email/телефона в payload audit.

## Примечание

Иммутабельный audit в БД для `platform_catalog_plans` остаётся в долге **1b-F7** / пересечение с **1a-F3** в [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md).
