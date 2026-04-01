# TPF_MODULE_LOYALTY — Абонементы и лояльность (Loyalty Engine)

> **Префикс TPF_** — Tech Passport Frontend. Модульный техпаспорт.  
> **Связь:** `TPF_MASTER.md` (разд. 4.8), `BUSINESS_LOGIC_V2.md` (§ 2.10), `ARCH_FRONTEND_BUSINESS_OS_UX.md` (§ 3.10), `REV_RAG_MAP_INNOVATIONS.md` (раздел 7b). Бэкенд: `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md` (Фаза B6).

---

## 1. Назначение

**Движок Лояльности и Капитала (Loyalty & Wealth Engine):** не «просто цифра 10→9», а уровень топовых фитнес-приложений и премиум-клиник. Удержание через пакеты услуг и депозиты, семейный шаринг, Zero-Click оплата с абонемента, AI-напоминания о сгорании, дашборд обязательств.

---

## 2. Блоки интерфейса

### 2.1. Digital Pass (Apple Wallet Style в PWA)

- **Где:** Приложение пациента (PWA), раздел «Мои абонементы» / профиль.
- **Визуал:** Абонементы — стопка градиентных карт (как банковские, с визуальным NFC-чипом). На карте: название пакета, прогресс-бар (крупный) «5 из 10», дата сгорания.
- **Действие:** Кнопка на карте `[Записаться по абонементу]` → открывается мастер записи (Booking Wizard) с отфильтрованными услугами пакета; на этапе чекаута — «Оплачено абонементом».
- **API:** `GET /api/v1/patient/loyalty/subscriptions` (или аналог) с полями: name, remaining/total (visits или amount), expires_at, services_included — для фильтра услуг в мастере записи.

### 2.2. Family Sharing (админка)

- **Где:** Drawer карточки пациента → вкладка **«Абонементы»**.
- **Логика:** Если у пациента есть пакет (депозит), отображается кнопка `[+ Добавить члена семьи]`. Открывается Spotlight-поиск по базе пациентов; выбранный пациент привязывается к пакету (FamilyLink). В PWA привязанного человека карта абонемента отображается с пометкой «Доступ предоставлен: [Имя владельца]».
- **API:** CRUD по связям FamilyLink; при списании визита проверка: пациент визита = владелец пакета ИЛИ в списке shared_with.

### 2.3. Auto-Checkout (Checkout Hub)

- **Где:** При переводе записи в «Завершено» открывается Checkout Hub (блок оплаты).
- **Smart Detection:** При открытии чекаута запрос `GET booking/{id}/checkout-info` (или в составе booking) возвращает список подходящих активных пакетов (package_id, name, remaining_visits/amount). Если пакет покрывает услугу визита — блок «Оплата» показывает галочку: `✅ Доступен абонемент «Курс Массажа». [Списать 1 визит]`. Админ нажимает «Подтвердить»; дублирование оплаты картой/наличными не допускается.
- **API:** При complete_booking опциональный параметр `use_subscription_id`; бэкенд вызывает use_subscription_for_booking только при его наличии.

### 2.4. Дашборд обязательств (Liability Dashboard)

- **Где:** Раздел «Финансы» — вкладка или блок для владельца.
- **Метрика:** «Деньги в воздухе» (Unearned Revenue) — сумма, которую клиенты заплатили за абонементы, но ещё не отходили (долг клиники перед клиентами).
- **API:** `GET /admin/clinics/{id}/finance/liability` или блок в отчёте; агрегат по остаткам активных CustomerSubscription (remaining_visits * условная цена или remaining_amount).

---

## 3. Эндпойнты

| Данные | Метод/путь | Примечание |
|--------|------------|------------|
| Пакеты пациента (PWA) | GET patient/loyalty/subscriptions | name, remaining/total, expires_at, services_included. |
| Подходящие пакеты для визита | GET booking/{id}/checkout-info или в составе booking | Список eligible subscriptions для Checkout Hub. |
| Завершение с абонементом | POST booking complete | Body: use_subscription_id (опционально). |
| Семья по пакету | GET/POST/DELETE admin/loyalty/packages/{id}/family | FamilyLink CRUD. |
| Liability | GET admin/clinics/{id}/finance/liability | Unearned Revenue. |

---

## 4. Правила UI

- Раздел Loyalty в меню BUSINESS: `/admin/loyalty` — список пакетов (шаблоны), проданные абонементы по клинике; при необходимости подразделы.
- В Drawer пациента вкладка «Абонементы»: список купленных пакетов + кнопка «+ Добавить члена семьи» для депозитов/пакетов с шарингом.
- Checkout Hub: при наличии подходящего абонемента — явная галочка «Списать с абонемента»; без ручного поиска пакета.
- EmptyState: «Нет абонементов» с CTA «Создать пакет» (в админке) / «Купить пакет» (в PWA по контексту).

---

## 5. Ссылки

- **Страницы:** `/admin/loyalty`, Drawer пациента (вкладка «Абонементы»), Checkout Hub, раздел Финансы (Liability). PWA: профиль / «Мои абонементы».
- **Сущности (бэкенд):** SubscriptionPackage, CustomerSubscription, SubscriptionUsage, FamilyLink (см. BUSINESS_LOGIC_V2.md § 2.10, DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md B6).
