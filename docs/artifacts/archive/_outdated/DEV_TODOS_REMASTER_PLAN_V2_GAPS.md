## DEV_TODOS_REMASTER_PLAN_V2_GAPS — хвосты по глобальному плану ремастера (V2)

> Основано на `ARCH_REMASTER_PLAN_V2.md` и текущих артефактах проекта.  
> Цель: зафиксировать, что нужно “докрутить” в управлении V2‑доставкой (документы, критерии готовности, quality gates).

---

## 1. Критерии готовности по фазам (Definition of Done)

- [ ] **1.1. DoD для каждого модуля V2**
  - Для AI/CRM/ERP/RBAC/Tasks/Loyalty/Paperless/Attribution/Frontend UX зафиксировать:
    - минимальный функциональный срез;
    - обязательные тесты (unit+integration, где нужно e2e);
    - минимальные security checks (RBAC/PII/логирование).

---

## 2. Quality gates (QA/SEC)

- [ ] **2.1. Матрица тестов V2**
  - Создать отдельный документ:
    - `docs/QA_TEST_MATRIX_V2.md`:
      - какие тесты есть сейчас;
      - каких не хватает;
      - какие тесты обязательны перед релизом.

- [ ] **2.2. Privacy/AI policy audit**
  - Создать:
    - `docs/SEC_PRIVACY_AND_AI_POLICY_AUDIT.md`:
      - точки, где может утечь ПДн (AI payload, логи, экспорт форм);
      - политика маскирования и RBAC‑правила;
      - тест‑кейсы на “не утекло”.

---

## 3. Документ‑источник правды по “контрактам”

- [ ] **3.1. Контракты событий, DTO и связей модулей**
  - Ввести документ:
    - `docs/ARCH_AUDIT_FINDINGS.md`:
      - event contracts;
      - “source of truth” по выручке/LTV/ROI;
      - инварианты multi‑tenancy.

---

## 4. Управление roadmap и премиум‑пакетами

- [ ] **4.1. Пакетирование Premium‑функций**
  - Зафиксировать “Premium набор”:
    - AI concierge;
    - Revenue Intelligence (ROI+LTV+smart tasks);
    - Paperless compliance pack.
  - Для каждого пакета: value proposition, зависимости, риски, критерии готовности.

