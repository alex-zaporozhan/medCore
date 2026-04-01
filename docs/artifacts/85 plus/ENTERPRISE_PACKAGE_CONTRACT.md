# ENTERPRISE_PACKAGE_CONTRACT

> **Назначение:** коммерческий контракт ENTERPRISE пакета для масштабного бизнеса (presale / procurement / governance review).  
> **Принцип:** никаких enterprise-обещаний без операционной доказуемости.

---

## 1) Для кого этот пакет

- Крупные сети и холдинги.
- Клиенты с высокими требованиями к governance, надежности, auditability и release safety.

---

## 2) Коммерческое обещание ENTERPRISE

1. Масштабируемая операционная система для мультифилиальной сети.
2. Прозрачная надежность с проверяемыми доказательствами.
3. Управляемая безопасность и контролируемый релизный контур.
4. Предсказуемость при росте нагрузки и организационной сложности.

---

## 3) Product scope: что входит / не входит

| Контур | Входит в ENTERPRISE | Не входит (без отдельного SoW) |
|--------|----------------------|----------------------------------|
| Booking/Operations | Полный контур с enterprise policy и расширенными контролями | Неформализованные кастомные бизнес-процессы |
| CRM/Analytics | Расширенные контуры, включая enterprise-level отчеты по policy | Функции, не подтверждённые edition/permission model |
| Multi-tenant/RBAC | Централизованный entitlement и tenant safety | “Временные” обходы policy для быстрых релизов |
| Integrations | Расширенный интеграционный контур в рамках согласованного профиля | Любая интеграция без контрактных SLA |
| Compliance/Operations | Release compliance, runbooks, drills, evidence lifecycle | Сертификации вне текущего регламента без отдельного проекта |

---

## 4) SLA/SLO обещание ENTERPRISE (целевой контракт)

| Метрика | Обещание ENTERPRISE | Условие валидности |
|---------|---------------------|--------------------|
| API availability (рабочее окно) | >= 99.9% (целевое) | Согласованный инфраструктурный профиль и on-call процесс |
| p95 latency (критичные API) | <= 300-500ms | Для согласованного enterprise load-профиля |
| Error rate критичных ручек | < 0.5-1% | При действующих release gates и observability |
| MTTR (P1/P2) | <= 60 мин (target <= 45) | При активных playbooks и эскалации |
| RPO/RTO | формально согласованы и проверены | Регулярные drill + documented evidence |

---

## 5) Обязательные доказательства до enterprise-сделки

1. Supply-chain compliance не ниже `C2` (желательно `C3`).
2. Integration gates (`G1..G8`) подтверждены evidence.
3. DB/Cache audit без открытых L3.
4. Есть минимум 1 полный подтвержденный “чистый” релизный цикл.
5. Есть incident/readiness пакет:
   - drills,
   - postmortem практика,
   - MTTR метрики.

Без этих пунктов нельзя заявлять enterprise-ready статус.

---

## 6) Стоп-обещания в enterprise-presale

1. Нельзя обещать “enterprise reliability by design” без production evidence.
2. Нельзя обещать entitlement/governance, если есть edition-policy разрывы.
3. Нельзя обещать release safety без signed compliance reports.
4. Нельзя обещать SLA выше подтверждённого operational baseline.

---

## 7) Enterprise presale checklist

| Вопрос | Да/Нет | Evidence |
|--------|--------|----------|
| Есть `C2+` compliance report? |  |  |
| Integration gate evidence полный? |  |  |
| Нет L3 по DB/Cache/Tenant/Edition? |  |  |
| Есть DR/incident доказательства? |  |  |
| SLA/SLO подтверждены метриками, а не планом? |  |  |

Если любой ответ “Нет” — enterprise-сделка в режиме повышенного риска.

---

## 8) Вердикт готовности ENTERPRISE к продаже

| Уровень | Условие | Решение |
|---------|---------|---------|
| E0 | Есть открытые critical/L3 | Не продавать как enterprise |
| E1 | Частичная зрелость, пилотный уровень | Ограниченный enterprise PoC |
| E2 | `C2+` + full evidence + закрытые L3 | Честно продаваемо enterprise |
| E3 | E2 + стабильная повторяемость на релизах | Сильная enterprise позиция |
