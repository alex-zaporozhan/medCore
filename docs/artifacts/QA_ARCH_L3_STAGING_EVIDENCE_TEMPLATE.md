# QA_ARCH — доказательства staging для Production Launch (L3)

**Среда:** staging  
**Дата прогона:** YYYY-MM-DD  
**Исполнитель QA_ARCH:** _имя_

> Использовать после выполнения [OPS_L3_PRODUCTION_GATE_CHECKLIST.md](../operations/OPS_L3_PRODUCTION_GATE_CHECKLIST.md). Ссылки на тикеты OPS/LEAD обязательны для перевода строк PRC в `satisfied`.

## OPS (ссылки)

| Пункт | Тикет / заметка | OK |
|-------|-----------------|----|
| ASM / секреты | | ☐ |
| Edge WAF webhook B | | ☐ |
| §17.1 (если replicas≥2) | | ☐ |
| Grafana auth / сеть | | ☐ |
| DR RPO/RTO §1 (если обновляли) | | ☐ |

## Публичный контур B / SaaS

| Сценарий | Результат (кратко) | OK |
|----------|-------------------|----|
| `GET /api/v1/public/platform/catalog/plans` — 200, валидный JSON | | ☐ |
| `POST /api/v1/public/platform/signup/checkout` — happy path или ожидаемая 503 без YooKassa | | ☐ |
| При включённом Turnstile — 403 `captcha_required` без токена | | ☐ |

## Кабинет Основателя / MFA

Чеклист: [LEAD_PLATFORM_FOUNDER_MFA_UX_CHECKLIST.md](./LEAD_PLATFORM_FOUNDER_MFA_UX_CHECKLIST.md)

| Сценарий | OK |
|----------|----|
| H2-1 … | ☐ |
| H2-2 … | ☐ |

## Алерты (1d)

| Сигнал | Доставка (Alertmanager / Telegram / webhook) | OK |
|--------|-----------------------------------------------|----|
| Тестовое срабатывание или реальный порог на staging | | ☐ |

## Итог

- **Готово к обновлению матрицы PRC:** да / нет  
- **Замечания:** _текст_

**Версия шаблона:** 2026-04-06
