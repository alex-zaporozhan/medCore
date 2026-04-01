## ARCH_SECURITY_PIPELINE — аудит зависимостей и security‑проверки перед релизом

Основание: `ARCH_HARDENING_ROADMAP.md` (п. 5), текущий стек: Python backend (FastAPI, SQLAlchemy, Redis), frontend (React + Vite/PWA), уже обнаруженные уязвимости (см. `DEVELOPMENT_PLAN.md` раздел про `npm audit`).

**Цель:** превратить аудит зависимостей и базовые security‑проверки в формальный, воспроизводимый шаг перед релизом (локально и в CI), с понятной политикой по уровням уязвимостей.

---

## 1. Область ответственности и охват

### 1.1. Что входит

- **Backend (Python):**
  - зависимости из `pyproject.toml` / `requirements.txt`;
  - используемые фреймворки (FastAPI, SQLAlchemy, Redis‑клиент, Celery при наличии).
- **Frontend (JS/TS):**
  - зависимости из `package.json` (react, vite, pwa‑плагины и т.п.);
  - только `dependencies` и `peerDependencies` (аудит `devDependencies` — опционален).

### 1.2. Что не входит (на этом уровне)

- Глубокий static analysis (Bandit, ESLint security‑rules, mypy на весь проект) — может быть добавлен отдельным ARCH‑документом;
- Pen‑testing, сторонние аудиты;
- Полная проверка инфраструктуры (Firewall/WAF, Kubernetes‑policies и т.п.) — зона `ARCH_PD_PROTECTION.md` + @OPS/@SEC.

---

## 2. Инструменты и команды

### 2.1. Backend (Python)

Рекомендуемые инструменты:

- `pip-audit` — официальный инструмент от PyPA;
- альтернативно/дополнительно `safety` (по внутреннему решению @SEC).

Базовые команды (пример):

```bash
pip-audit -r requirements.txt --progress-spinner=off
```

или, если используется `pyproject.toml`:

```bash
pip-audit --progress-spinner=off
```

**Требования:**

- команды должны:
  - выполняться без интерактивного ввода;
  - возвращать ненулевой код выхода при критичных/высоких уязвимостях;
  - быть оформлены в виде:
    - либо Makefile‑таргетов (`make security-backend`),
    - либо скриптов `scripts/security_backend.sh`,
    - либо `tox`/`nox`‑env’ов (по выбору @DEV).

### 2.2. Frontend (Node)

Рекомендуемый инструмент:

- `npm audit --production` (или `pnpm audit`, если используется другой менеджер пакетов).

Базовая команда:

```bash
npm audit --production --audit-level=high
```

**Требования:**

- использовать флаг `--production`, чтобы фокусироваться на боевых зависимостях;
- не запускать `npm audit fix --force` автоматически в CI;
- оформить команду как npm‑скрипт, например:

```json
{
  "scripts": {
    "security:audit": "npm audit --production --audit-level=high"
  }
}
```

---

## 3. Политика по уровням уязвимостей

Уровни (как обычно в CVE/инструментах):

- **critical**
- **high**
- **medium**
- **low**
- **info** (опционально)

### 3.1. Backend

Политика:

- **critical / high**:
  - блокируют релиз;
  - require action: обновление зависимостей, патчи, либо документированное обоснование исключения (waiver) с дедлайном;
- **medium**:
  - не блокируют релиз автоматически, но:
    - должны быть зафиксированы в issue/baclog;
    - при накоплении нескольких medium‑уязвимостей вокруг одной зависимости инициируется задача на обновление.
- **low / info**:
  - вносятся в отчёт, но не блокируют релиз;
  - решаются по мере удобства.

Исключения:

- в редких случаях может быть принято решение **временно игнорировать** отдельную high‑уязвимость (например, во второстепенной утилите), если:
  - эксплойт практически невозможен в конкретном окружении;
  - есть чёткое письменное обоснование от @SEC/@LEAD;
  - создана задача на устранение с конкретным сроком.

### 3.2. Frontend

Политика:

- **critical / high**:
  - блокируют релиз, если затрагивают:
    - `dependencies`/`peerDependencies`;
    - цепочку сборки PWA (например, `vite-plugin-pwa`, `workbox` и т.п.), которая попадает на prod.
  - если уязвимость только в `devDependencies` (storybook, dev‑tools):
    - решение по блокировке принимается @LEAD/@SEC, но по умолчанию высокие уязвимости тоже считаются нежелательными.
- **medium / low**:
  - фиксируются в backlog;
  - могут копиться до планового окна обновлений зависимостей.

---

## 4. Минимальный CI‑pipeline

CI‑система может быть любой (GitHub Actions, GitLab CI, TeamCity и т.п.). Ниже — абстрактный скелет.

### 4.1. Этапы пайплайна

1. **Lint & tests (существующий):**
   - запуск unit‑тестов backend/frontend;
   - базовые линтеры.
2. **Security audit backend:**
   - установка зависимостей backend;
   - запуск `pip-audit`/`safety`.
3. **Security audit frontend:**
   - установка `node_modules` (с учётом `NODE_ENV=production`);
   - запуск `npm run security:audit` (или аналогичной команды).

### 4.2. Пример псевдо‑конфига CI

```yaml
jobs:
  security-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install backend dependencies
        run: pip install -r requirements.txt pip-audit
      - name: Run pip-audit
        run: pip-audit -r requirements.txt --progress-spinner=off

  security-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Install frontend dependencies
        run: npm ci
      - name: Run npm audit
        run: npm run security:audit
```

Реальный конфиг должен учитывать кеширование зависимостей, matrix‑сборки и т.п.

### 4.3. Критерий "pass/fail"

- Джоб **failed** (и блокирует merge/release), если:
  - инструмент вернул ненулевой код выхода по найденным critical/high уязвимостям;
  - или при post‑обработке отчёта (если добавится) обнаружены такие уязвимости.
- Джоб **success**:
  - при отсутствии critical/high;
  - либо при наличии за‑waiver’енных уязвимостей, явно подавленных с документированным решением.

---

## 5. Рабочий процесс (workflow) для @DEV, @QA, @SEC, @OPS

### 5.1. Перед релизом

1. @DEV выполняет security‑команды локально:
   - `pip-audit` / `safety`;
   - `npm run security:audit`.
2. Фиксит очевидные/простые уязвимости (обновление патч‑версий, замена небезопасных пакетов).
3. При сложных случаях:
   - выносит результаты в отдельный отчёт/issue;
   - согласует приоритезацию с @LEAD/@SEC.

### 5.2. В CI

- При каждом merge‑request в основную ветку:
  - security‑джобы запускаются как часть пайплайна;
  - при fail — merge блокируется до решения.

### 5.3. Роль @QA/@SEC

- @QA:
  - проверяет, что security‑джобы входят в чек‑лист перед релизом;
  - при наличии открытых high/critical уязвимостей помечает релиз как условный/заблокированный.
- @SEC:
  - периодически просматривает отчёты `pip-audit`/`npm audit`;
  - принимает решения по исключениям (waivers) и срокам их закрытия;
  - при необходимости обновляет этот ARCH‑документ.

---

## 6. Выход для цепочки

Этот документ задаёт:

- набор **обязательных инструментов** (`pip-audit`/`safety`, `npm audit --production`);
- **политику по критичности** уязвимостей (что блокирует релиз, что идёт в backlog);
- минимальный **скелет CI‑pipeline**;
- понятный workflow между @DEV/@QA/@SEC/@OPS.

В контексте `DEV_PROMPTS_HARDENING_SECURITY_AND_AI.md` (фаза B.1) @DEV должен:

- добавить соответствующие команды/скрипты в backend/frontend;
- убедиться, что они воспроизводимы локально;
- подготовить основу для интеграции в CI по этому ARCH‑документу.

