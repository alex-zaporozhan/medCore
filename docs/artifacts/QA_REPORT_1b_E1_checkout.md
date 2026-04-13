# QA_ARCH: срез 1b-E1 — публичный каталог + checkout

**Дата:** 2026-04-06  
**Epic:** 1b-E1  
**Статус:** закрыт по минимальному DoD (API + гейт суммы на webhook; UI на лендинге)

## Реализация

| Компонент | Описание |
|-----------|----------|
| Каталог | `GET /api/v1/public/platform/catalog/plans` (уже было) |
| Checkout | `POST /api/v1/public/platform/signup/checkout` — `email`, `plan_slug`, `billing_period` (`monthly` \| `annual`), сумма из `platform_catalog_plans`, `tariff_snapshot` с `billing_period` |
| Провайдер | YooKassa `create_platform_subscription_payment` в `yookassa_client.py` |
| Гейт суммы | По-прежнему `evaluate_platform_payment_against_catalog` на webhook (существующие тесты) |
| UI | Лендинг `frontend/src/App.tsx` (`LandingPage`): email, кнопки «Оплатить (месяц/год)» |
| Тесты | `tests/api/test_public_platform_checkout.py` |

## DoD

- [x] Публичный каталог (ранее) + checkout с `billing_period` и ценой из каталога.
- [x] Тесты гейта суммы на контуре B (наследие) + новые тесты checkout (stub YooKassa).
- [x] UI согласован с FE-E1 (минимальный self-service на главной маркетинговой странице).

## Примечания

- Требуется `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET_KEY` и return URL (`platform_saas_checkout_return_url` или `yookassa_return_url`).
- Повторяющиеся edge-кейсы антиспама и полный маркетинговый лендинг — см. **1b-F3** / **10_CROSS_CUTTING**.
