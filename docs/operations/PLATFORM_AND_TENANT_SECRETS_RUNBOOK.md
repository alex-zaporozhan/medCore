# Секреты платформы и контура B (PRC-A3)

Краткий runbook для продакшена: **не хранить** критичные секреты только в `.env` на ВМ без внешнего хранилища.

## Обязательные переменные (выдержка)

| Секрет / ключ | Назначение |
|----------------|------------|
| `PLATFORM_BILLING_WEBHOOK_SECRET` | Заголовок `X-Platform-Billing-Webhook-Secret` для контура B |
| `PLATFORM_FOUNDER_JWT_SECRET` | Подпись JWT Основателя (`/platform/internal/*`) |
| `JWT_SECRET_KEY` / `SECRET_KEY` | Тенантский контур, сессии |
| `YOOKASSA_SECRET_KEY` | Провайдер оплат (общий ключ магазина) |

## Рекомендуемая практика

1. **Хранилище:** AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault, или встроенные секреты оркестратора (Kubernetes Secret + SealedSecrets/External Secrets).
2. **AWS Secrets Manager (реализация в приложении):** задать `AWS_SECRETS_MANAGER_SECRET_ID` (ARN или имя секрета). **SecretString** — JSON-объект `{"ENV_NAME":"value",...}`. Перед загрузкой `pydantic` Settings значения **дописываются** в `os.environ`, если переменная ещё пустая (локальный `.env` и явные env в compose имеют приоритет). Регион: `AWS_SECRETS_MANAGER_REGION` или `AWS_REGION`. При `TESTING=1` загрузка **отключена**. Код: `src/core/runtime_secrets.py`, вызов из `src/core/config.py`.
3. **Подача в процесс:** mount/env из рантайма CI/CD; ротация без коммита в git.
4. **Ротация:** отдельный OPS-тикет; для webhook B — обновить значение в провайдере и в приложении в одном окне.
5. **Доступ:** least privilege; аудит чтения секретов где доступно.

## Закрытие PRC-A3 (`satisfied` в матрице)

**В репозитории уже есть:** загрузка JSON из AWS Secrets Manager до Settings (`src/core/runtime_secrets.py`), fail-closed старт в production при пустых критичных секретах (`assert_required_security_secrets_in_production` в `payment_webhook_governance`), тесты `tests/core/test_payment_webhook_governance.py`.

**В среде production (OPS-тикет, обязательно для перевода PRC-A3 из `in_progress`):**

1. Создать секрет в AWS Secrets Manager (или утверждённом vault) с JSON ключами как минимум для: `PLATFORM_BILLING_WEBHOOK_SECRET`, `PLATFORM_FOUNDER_JWT_SECRET`, `JWT_SECRET_KEY`, `PATIENT_PAYMENT_WEBHOOK_SECRET`, при необходимости `SECRET_KEY`, провайдерских ключей.
2. Выдать роли выполнения `GetSecretValue` только нужным сервис-аккаунтам/API (least privilege).
3. В деплое задать `AWS_SECRETS_MANAGER_SECRET_ID` и регион; убедиться, что процесс API при старте подхватывает значения (лог `runtime_secrets: merged N keys`, отсутствие `RuntimeError` на bootstrap).
4. Зафиксировать в тикете: ARN секрета (без значений), дата, исполнитель — **закрытие артефакта PRC-A3 для LEAD/QA_ARCH**.

Пока пункты 1–4 не выполнены в реальной среде, статус **PRC-A3** остаётся `in_progress` при зелёном коде в git.

## Связанные документы

- [FOUNDER_ACCESS_BREAKGLASS.md](./FOUNDER_ACCESS_BREAKGLASS.md)
- [PRC_STAGING_EVIDENCE_CHECKLIST.md](./PRC_STAGING_EVIDENCE_CHECKLIST.md) (смежные OPS-доказательства)
- [deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md](../../deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md)
- МП §9, §12

**Версия:** 2026-04-08 (DEV + OPS)
