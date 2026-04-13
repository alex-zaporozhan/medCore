# 📁 FILE_MAP — Структура проекта

> Где живёт каждый файл. @CREATOR и @LEAD создают файлы согласно этой карте.

---

## КОРЕНЬ ПРОЕКТА (/)

```
.cursorrules          ← конституция системы (читается на КАЖДОМ запросе)
.env                  ← секреты (НИКОГДА не в git)
.env.example          ← шаблон переменных (в git)
.gitignore
docker-compose.yml
Makefile              ← make up / down / logs / backup
README.md             ← только для клиента (запуск, настройка)
```

---

## /docs — система ролей и протоколы

**Роли (читаются по @mention):**
```
docs/ROLE_LEAD.md
docs/ROLE_CREATOR.md
docs/ROLE_ARCH.md
docs/ROLE_DEV.md
docs/ROLE_QA.md
docs/ROLE_SEC.md
docs/ROLE_AUDITOR.md
docs/ROLE_FRONTEND.md
docs/ROLE_OPS.md
docs/ROLE_BIZ.md
docs/ROLE_PERF.md
docs/ROLE_LAWYER.md       ← только перед передачей клиенту
```

**Системные документы:**
```
docs/ENGINEERING_PLAN.md  ← машина состояний, Transmission Protocol, Quality Gate
docs/STACK_SELECTION.md   ← режимы, стек, Docker ENV crystal
docs/PROCESS_LAUNCH.md    ← фазы запуска продукта (MVP → стабильность → рост)
docs/TESTING_CANON.md     ← база категорий проверок для @QA и @AUDITOR
docs/LOGGING_AND_DEBUGGING.md  ← (удалён, принципы в ролях)
```

**Шаблоны:**
```
docs/TEMPLATE_BIZ_LOGIC.md
docs/TEMPLATE_COMMERCIAL_PACK.md
docs/TEMPLATE_MODULE_DEV.md   ← стандарт разработки модулей; @ARCH при планировании любого модуля
docs/DEPLOY_LICENSE_AND_PIRACY.md
```

**Опциональные:**
```
docs/CRYSTALS.md          ← только по предложению @LEAD + подтверждению пользователя
docs/SELF_LEARNING.md     ← только по явному запросу пользователя
```

---

## /docs — живые артефакты проекта (создаёт @CREATOR и @ARCH)

**@CREATOR / продукт:**
```
docs/artifacts/BUSINESS_LOGIC.md    ← канон бизнес-правил (слой W)
```

**@ARCH:**
```
docs/artifacts/SAAS_ARCHITECTURE_SPINE_2026.md  ← главный каркас; точечно ARCH_MODULE_*
docs/artifacts/BUSINESS_ROUTES.md · docs/ARCH_FRONTEND_UI_LOGIC.md ← перед фронтендом
```

**@LEAD:**
```
docs/artifacts/DEVELOPMENT_PLAN.md  ← текущий фокус и журнал
docs/DEVELOPMENT_PLAN.md            ← только указатель на artifacts (не дублировать)
docs/product_state/               ← выходы @SCRIBE (слой S)
```

**Отчёты ролей (по необходимости):**
```
docs/QA_[ПРОЕКТ].md
docs/SEC_[ПРОЕКТ].md
docs/AUDITOR_[ПРОЕКТ]_[ТЕМА].md
docs/OPS_[ПРОЕКТ].md
```

**Коммерческий пакет (после деплоя):**
```
docs/COMMERCIAL_PACK_[ПРОЕКТ].md
```

---

## /deploy — финальная сборка для клиента (@OPS)

```
deploy/
├── docker-compose.yml
├── .env.example
├── nginx.conf          ← если нужен
├── Makefile
├── LICENSE.txt         ← @LAWYER заполняет перед передачей
└── README.md           ← ТОЛЬКО для клиента
```

---

## Правила

**В git идёт:** всё кроме `.env`, `deploy/` с реальными секретами, `__pycache__`, node_modules.

**@CREATOR создаёт:** только `BUSINESS_LOGIC.md` — всё остальное по Transmission Protocol передаёт @LEAD.

**Артефакты обновляются на месте** — не создаются новые файлы типа `ARCH_v2.md` или `SYS_*_CHANGELOG`. Git хранит историю.

**План @LEAD:** `docs/artifacts/DEVELOPMENT_PLAN.md`. Карта папок: `docs/DOC_TOPOLOGY.md`.
