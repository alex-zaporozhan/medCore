## 🧭 ROADMAP_NEXT_STEPS — где мы сейчас и что дальше

> Этот файл — срез состояния реаудита и архитектуры vNext  
> и пошаговый план, от которого можно оттолкнуться в новом контексте.

---

## 1. Текущее состояние (что уже сделано)

- **Аудит и бизнес‑логика**
  - `BUSINESS_LOGIC_CURRENT.md` (архив) — фактическая логика по коду v1.
  - `BUSINESS_LOGIC_V2.md` (архив) — целевая Business OS.
  - `BUSINESS_ROUTES.md` — фактическая карта маршрутов backend/frontend и их сопоставление с бизнес‑логикой.
  - `QA_AUDIT_NEXT.md` — аудит поведения продукта (пациент/админ), GAPS G1–G12.

- **Архитектура vNext**
  - `ARCH_DECISIONS_NEXT.md` — принципы архитектуры, домены, инварианты.
  - Доменные файлы:
    - `ARCH_BOOKING_NEXT.md`
    - `ARCH_CRM_NEXT.md`
    - `ARCH_ERP_NEXT.md`
    - `ARCH_LOYALTY_NEXT.md`
    - `ARCH_OMNICHANNEL_NEXT.md`
    - `ARCH_TASKS_NEXT.md`
    - `ARCH_PAPERLESS_NEXT.md`
    - `ARCH_ATTRIBUTION_NEXT.md`
  - `ARCH_AUDIT_NEXT.md` — аудит согласованности «код ↔ ARCH ↔ BUSINESS» + рекомендации для ARCH и DEV_PROMPTS.

- **Backend/Frontend/Non‑functional GAPS**
  - Backend:
    - `BACKEND_GAPS_Booking_NEXT.md`
    - `BACKEND_GAPS_CRM_NEXT.md`
    - `BACKEND_GAPS_ERP_NEXT.md`
    - `BACKEND_GAPS_Loyalty_NEXT.md`
    - `BACKEND_GAPS_Omnichannel_NEXT.md`
    - `BACKEND_GAPS_Tasks_NEXT.md`
    - `BACKEND_GAPS_Paperless_NEXT.md`
    - `BACKEND_GAPS_Attribution_NEXT.md`
    - `BACKEND_GAPS_SUMMARY_NEXT.md`
  - Frontend:
    - `UX_FLOWS_AND_GAPS_NEXT.md`
    - `FRONTEND_GAPS_Admin_NEXT.md`
    - `FRONTEND_GAPS_AppPWA_NEXT.md`
    - `FRONTEND_GAPS_Omnichannel_NEXT.md`
    - `FRONTEND_GAPS_SUMMARY_NEXT.md`
  - Нефункциональный аудит:
    - `NONFUNCTIONAL_AUDIT_NEXT.md` (SEC/PERF/OBS).

- **Бизнес‑план и dev‑план**
  - `BUSINESS_PLAN_NEXT.md` — видение Business OS vNext с явной привязкой к GAPS.
  - `DEV_PROMPTS_NEXT.md` — полный список DEV_PROMPT_xxx по доменам + приоритеты и зависимости.

- **Первый ARCH_DEV‑артефакт (политика AI/ПД)**
  - `ARCH_DEV_OMNI_POLICY_016.md`:
    - описывает целевую политику AI/ПД:
      - все внешние AI‑вызовы только через `SafeAiClient` + `AiSanitizer`;
      - строгую логику `allow_personal_data` по `ClinicAiSettings.ai_provider_type` и `ai_enabled`;
      - использование `AiConfigService` как единого источника правды;
      - необходимость расширяемого санитайзера для маскировки не только телефона/email, но и ФИО/адресов/паспорта в будущем;
    - содержит dev‑чек‑лист для DEV_PROMPT_OMNI_POLICY_016.

---

## 2. Усиленная защита ПД и AI‑политика (что важно зафиксировать)

1. **Требование РФ по ПД:**  
   мы рассматриваем любые внешние AI‑провайдеры (Claude, OpenAI и т.п.) как _потенциально трансграничных_,  
   поэтому:
   - по умолчанию `allow_personal_data=False` для `provider_type="external"`, даже если клиника «включила AI»;
   - передача ФИО, телефонов, e‑mail, адресов и любых иных идентификаторов во внешние LLM **запрещена по умолчанию** и может быть включена только:
     - при `provider_type in {"ru_compliant", "on_premise"}`;
     - и `ai_enabled=True`.

2. **Расширяемый AiSanitizer (обязать к реализации в одном из следующих ARCH_DEV):**
   - сейчас маскируются телефон и e‑mail;
   - нужно архитектурно закрепить:
     - возможность добавлять новые типы детекторов (ФИО, адреса, реквизиты) через расширяемый механизм (регексы/плагины/конфиг);
     - тесты, подтверждающие, что при `allow_personal_data=False` никакие очевидные ПД не проходят наружу;
     - явное логирование «маскируем/не маскируем» только без утечек исходного текста.

3. **Единый слой политики для всех AI‑вызовов:**
   - Omnichannel Orchestrator, Chat AI, AI‑анализ диалогов, AI‑Tasks, любые будущие AI‑модули  
     обязаны:
     - использовать `AiConfigService` / AI‑factory для SafeAiClient;
     - не создавать `AiClient` напрямую для внешних вызовов;
     - не переопределять `allow_personal_data` в обход политики.

Эти требования уже заложены в `ARCH_DEV_OMNI_POLICY_016.md`, но должны быть **взяты в работу** при реализации соответствующих DEV_PROMPTS.

---

## 3. План следующих шагов (высокоуровневый)

### 3.1. ARCH_DEV‑уровень (без кода)

Мы договорились о шаблоне:  
**для каждой приоритетной DEV_PROMPT_xxx → отдельный ARCH_DEV_xxx.md → dev‑чек‑лист.**

Приоритет по зависимостям (см. `DEV_PROMPTS_NEXT.md`):

1. **Безопасность и AI‑политика (P0)**
   - Уже есть:
     - `ARCH_DEV_OMNI_POLICY_016.md` для DEV_PROMPT_OMNI_POLICY_016;
     - `ARCH_DEV_SEC_RBAC_022.md` для DEV_PROMPT_SEC_RBAC_022:
       - карта ролей/пермишенов по доменам (ERP, CRM, Loyalty, Tasks, Attribution, AI‑settings);
       - список всех чувствительных эндпоинтов и требуемых пермишенов;
       - dev‑чек‑лист по проверке/добавлению `require_permissions(...)` и тестам.

2. **ERP‑узел и завершение визита (P0–P1)**
   - Подготовить:
     - `ARCH_DEV_BKG_CORE_001.md` (фасад завершения визита, стык Booking↔ERP↔CRM↔Loyalty);
     - `ARCH_DEV_ERP_NODE_010.md` (детализация ERP‑узла и его взаимодействия с фасадом);
     - `ARCH_DEV_ERP_LOYALTY_011.md` (integraция ERP с ლояльностью, обязательства/авансы);
     - `ARCH_DEV_ERP_REPORTS_012.md` (владельческая отчётность).

3. **Нормализация статусов и UX‑словари (P1)**
   - `ARCH_DEV_BKG_STATE_002.md`:
     - единый enum/словарь статусов Booking;
     - мэппинги в backend и frontend;
     - список страниц/компонентов, которые нужно обновить.

4. **Наблюдаемость и цепочки (P1)**
   - `ARCH_DEV_OBS_CHAINS_023.md`:
     - перечисление критичных цепочек (Booking→ERP/CRM/Loyalty, Omnichannel+AI, CRM+Attribution и др.);
     - какие логи/метрики нужны на каждом шаге;
     - dev‑чек‑лист по их внедрению.

5. **Дальше — по блокам (Omnichannel & AI, CRM, Loyalty, Paperless, Tasks, Perf)**
   - Для каждого DEV_PROMPT из `DEV_PROMPTS_NEXT.md` по приоритету:
     - создать соответствующий `ARCH_DEV_*` файл;
     - расписать архитектурные решения и dev‑чек‑листы.

### 3.2. DEV‑уровень (когда будем готовы писать код)

Когда ARCH_DEV‑слой подготовлен хотя бы для P0/P1‑задач:

1. Выбираем одну конкретную DEV‑таску (например, DEV_PROMPT_OMNI_POLICY_016).
2. Открываем её `ARCH_DEV_*` файл.
3. Пошагово выполняем dev‑чек‑лист:
   - читаем и меняем указанные файлы;
   - добавляем/обновляем тесты;
   - прогоняем сценарии.
4. Отмечаем в:
   - `DEV_PROMPTS_NEXT.md` — что задача частично/полностью выполнена;
   - соответствующих `*_GAPS_*_NEXT.md` — какие GAPS закрыты.

Важно: **на этом этапе архитектурные решения уже приняты**, DEV не придумывает бизнес‑ или архитектурные компромиссы, а только качественно реализует план.

---

## 4. Что критично не забыть в новом контексте

1. **Основные артефакты для старта нового окна:**
   - `BUSINESS_PLAN_NEXT.md`
   - `ARCH_DECISIONS_NEXT.md`
   - все `ARCH_*_NEXT.md`
   - `ARCH_AUDIT_NEXT.md`
   - `QA_AUDIT_NEXT.md`
   - все `BACKEND_GAPS_*_NEXT.md` и `FRONTEND_GAPS_*_NEXT.md` + SUMMARY
   - `NONFUNCTIONAL_AUDIT_NEXT.md`
   - `DEV_PROMPTS_NEXT.md`
   - `ARCH_DEV_OMNI_POLICY_016.md`
   - (по мере появления) остальные `ARCH_DEV_*`.

2. **Жёсткие правила, которые уже зафиксированы:**
   - «Нет GAPS без DEV_PROMPT’а».
   - Запрет на «возможно есть в коде» при доступе к исходникам — сначала исследуем, потом вывод.
   - Opinionated defaults: если пользователь не уточняет, роли сами принимают сильные решения, опираясь на код/архитектуру и лучшие практики.
   - AI‑слой всегда потребляет доменные сервисы, никогда не обходит их и не пишет напрямую в БД.

С этого файла можно начинать новый диалог: он даёт честную картину «где мы» и **какой следующий крупный шаг** логичнее всего сделать.

