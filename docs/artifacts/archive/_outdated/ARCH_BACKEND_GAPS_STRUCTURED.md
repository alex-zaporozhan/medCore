# ARCH_BACKEND_GAPS_STRUCTURED — Структурированные пробелы бэкенда для полной сборки

> **Роль:** @ARCH. Исходный список — `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_GAPS.md`. Здесь — приоритизация, зависимости и привязка к фазам фронта.  
> **Следующий шаг:** выполнение по промпту `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md`.

---

## Приоритеты

| Приоритет | Смысл | Блоки |
|-----------|--------|--------|
| **P0** | Блокирует фронт по DEV_MASTER_PROMPT (Фазы 1–2) или критичен для чекаута/форм | Summary (HoverCard), form send-link, Feed claim, suggest-slots, booking from waitlist, POST finance/transactions, CRM aggregates, Tasks source+claim |
| **P1** | Нужен для полных карточек и аналитики (Фазы 3–4) | Rich entity DTOs, AI Marketing Advisor (заглушка или контракт), Checkout eligible subscriptions + use_subscription_id |
| **P2** | Дифференциаторы и Loyalty Engine (Фазы 5 + Loyalty) | admin/search, POST ai/agent, saved revenue widget, Retention AI, Media/Export/Backup, FamilyLink, Liability, check_expiring_packages, COUNT/BALANCE |

---

## Зависимости между блоками

```
P0:  [summary] [form send-link] [feed claim] [suggest-slots] [booking from waitlist]
       |              |              |              |                    |
       v              v              v              v                    v
     Фронт 1       Фронт 2.4      Фронт 2.1     Фронт 2.3           Фронт 2.3

P0:  [POST finance/transactions]  [CRM stage aggregates]  [Tasks source=ai + claim]
       |                              |                            |
       v                              v                            v
     Фронт 4.3                      Фронт 4.1                   Фронт 4.2

P1:  [Rich Patient/Booking/Doctor/Service]  [Checkout eligible subs]  [Dashboard 4 metrics]
       |                                        |                            |
       v                                        v                            v
     Фронт 3                                   Фронт 4.3                   Фронт 2.1

P2:  [search] [ai/agent] [saved revenue] [Retention] [Media/Export/Backup]
     [FamilyLink] [Liability] [check_expiring_packages] [COUNT/BALANCE]
       |
       v
     Фронт 5 + Loyalty UI
```

---

## Маппинг на фазы фронта (DEV_MASTER_PROMPT)

| Фаза фронта | Необходимый бэкенд (из BACKEND_GAPS) |
|-------------|--------------------------------------|
| 1 | Patient/Doctor summary; POST form/send-link |
| 2 | Dashboard 4 метрики; Attention Feed claim; suggest-slots; booking from waitlist; form send-link |
| 3 | Rich entity (вложенные коллекции или подзапросы по вкладкам) |
| 4 | CRM stage aggregates; Tasks source=ai + claim; POST finance/transactions; AI Marketing Advisor |
| 5 | admin/search; POST ai/agent; saved revenue; Retention AI; Media; Export Builder; Full Backup |
| Loyalty (в DEV_MASTER не отдельная фаза, но в BACKEND_GAPS есть) | FamilyLink; Checkout eligible subscriptions + use_subscription_id; Liability; check_expiring_packages; COUNT/BALANCE; PWA Digital Pass |

---

## Контракты (кратко)

Полные контракты и пошаговые инструкции для @DEV — в `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md`. Здесь только ссылка на секции того документа.

- **B1 (P0):** Summary, form send-link — § B1.
- **B2 (P0):** Dashboard 4 метрики, Feed claim, suggest-slots, booking from waitlist — § B2.
- **B3 (P1):** Rich Patient/Booking/Doctor/Service — § B3.
- **B4 (P0/P1):** CRM aggregates, Tasks source+claim, POST finance/transactions, Checkout eligible subs — § B4.
- **B5 (P2):** search, ai/agent, saved revenue, Retention, Media, Export, Backup — § B5.
- **B6 (P2):** Loyalty Engine (FamilyLink, Liability, check_expiring_packages, COUNT/BALANCE, Digital Pass) — § B6.

---

*Использование: при планировании спринта брать блоки из этого документа в порядке P0 → P1 → P2; детали и шаги — в DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md.*
