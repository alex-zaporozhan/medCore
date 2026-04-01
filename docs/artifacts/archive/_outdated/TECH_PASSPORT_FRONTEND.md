## 🎨 TECH_PASSPORT_FRONTEND — Dental Booking (Frontend)

Режим:    SAAS  
Backend:  Python 3.11 + FastAPI (отдельный паспорт)  
Frontend: TypeScript + React 18 + Mantine + React Router + React Query + Vite + PWA  
БД:       Использует REST‑API backend (PostgreSQL/Redis/Celery), прямого доступа к БД нет  
Почему:   Современный SPA/PWA‑стек с быстрым DX, лёгкой темизацией и хорошей интеграцией с REST‑API.

---

## 1. Общий обзор

- **Тип приложения**: одностраничное приложение (SPA) на React 18, упаковано через Vite, c PWA‑обвязкой.
- **Назначение**:
  - Пациентское PWA‑приложение (`/app`, `/login`, `/oauth/result`, `/booking/success`).
  - Веб‑админка клиники (`/admin/*`).
  - Лэндинг‑страница выбора роли (`/`).
- **Основные обязанности**:
  - Авторизация пациента по телефону + SMS‑код либо через OAuth (VK, Yandex).
  - Авторизация администратора по email/паролю.
  - Визуализация расписания, услуг, записей, предоплаты и листа ожидания.
  - Интерфейс омниканального чата и AI‑ассистента для админов.
  - Настройка интеграций, уведомлений, предоплаты, стилей и маркетинговых материалов.

Ключевые файлы запуска:

- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`

---

## 2. Технологический стек (runtime и tooling)

- **Язык**: TypeScript `~5.6.2`.
- **Фреймворк**: React `18.3.1`.
- **UI‑библиотека**: Mantine `^7.15.0` (`@mantine/core`, `@mantine/hooks`).
- **Роутинг**: React Router DOM `^6.28.0` (используется `createBrowserRouter` и `createRoutesFromElements`).
- **Стейт и данные**:
  - `@tanstack/react-query` `^5.62.0` — загрузка и кеширование данных.
  - Локальные React‑контексты (`PatientAuthContext`, `AdminClinicContext`) + `localStorage` для токенов.
- **Drag & Drop**: `@dnd-kit/core`, `@dnd-kit/utilities` — календарная сетка/drag‑and‑drop в админке.
- **Дата/время**: `dayjs` `^1.11.13`.
- **Смайлики**: `@emoji-mart/data`, `@emoji-mart/react` — стикеры/эмодзи в чатах.
- **Сборка и dev‑сервер**:
  - Vite `^6.0.1` + `@vitejs/plugin-react` `^4.3.4`.
  - Конфиг: `frontend/vite.config.ts`.
- **PWA**:
  - `vite-plugin-pwa` `^0.21.1`.
  - Регистрация сервис‑воркера: `frontend/src/pwa/registerPwa.ts`.
- **Тестирование и качество**:
  - `vitest` `^2.1.4` + `@testing-library/react` + `@testing-library/jest-dom`.
  - `postcss` + `postcss-preset-mantine` + `postcss-simple-vars` для обработки стилей.

---

## 3. Точка входа и структура приложения

### 3.1. Входной модуль

```12:32:d:\CURSOR\projects\dental_booking\frontend\src\main.tsx
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ColorSchemeScript defaultColorScheme="light" />
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={appTheme} defaultColorScheme="light">
        <App />
      </MantineProvider>
    </QueryClientProvider>
  </React.StrictMode>
);

registerPwa();
```

- Оборачивает приложение в:
  - `QueryClientProvider` (React Query).
  - `MantineProvider` с темой `appTheme` и светлой схемой по умолчанию.
  - `React.StrictMode`.
- Регистрирует PWA через `registerPwa()`.

### 3.2. Корневой роутер

```110:197:d:\CURSOR\projects\dental_booking\frontend\src\App.tsx
const router = createBrowserRouter(
  createRoutesFromElements(
    <>
      <Route path="/" element={<LandingPage />} />
      <Route path="/admin" element={<AdminAuthGuard />}>
        <Route path="login" element={<AdminLoginPage />} />
        <Route
          path=""
          element={
            <AdminClinicProvider>
              <ErrorBoundary>
                <AdminLayout />
              </ErrorBoundary>
            </AdminClinicProvider>
          }
        >
          <Route index element={<AdminDashboardPage />} />
          ...
        </Route>
      </Route>
      <Route
        path="/login"
        element={
          <PatientAuthProvider>
            <LoginPage />
          </PatientAuthProvider>
        }
      />
      <Route
        path="/oauth/result"
        element={
          <PatientAuthProvider>
            <OAuthResultPage />
          </PatientAuthProvider>
        }
      />
      <Route
        path="/app"
        element={
          <PatientAuthProvider>
            <AppLayout />
          </PatientAuthProvider>
        }
      >
        <Route index element={<HomePage />} />
        <Route path="feed" element={<FeedPage />} />
        <Route path="booking" element={<BookingWizardPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="chat" element={<ChatPage />} />
      </Route>
      <Route path="/booking/success" element={<BookingSuccessPage />} />
    </>
  ),
  { future: { v7_relativeSplatPath: true } }
);
```

- **Лэндинг (`/`)**:
  - `LandingPage` — карточка с выбором «Приложение пациента» (`/app`) и «Админка» (`/admin`).

- **Админка (`/admin`)**:
  - Обёртка `AdminAuthGuard`:
    - Защищает внутренние роуты, перекидывает неавторизованных админов на `/admin/login`.
  - Внутри:
    - `/admin/login` → `AdminLoginPage`.
    - Корневой layout:
      - `AdminClinicProvider` — выбирает текущую клинику и бизнес‑лексикон.
      - `AdminLayout` — общий каркас админки (меню, хедер, контент).
    - Вложенные страницы:
      - `index` → `AdminDashboardPage`.
      - `clinics`, `services`, `schedule`, `bookings`, `prepayment`, `waitlist`, `recall`,
        `marketing`, `attention`, `reports`, `doctors`, `doctor-schedule`, `patients`,
        `omni-chat`, `omni-channels`, `omni-ai-settings`, `channels`, `integrations`,
        `styling`, `stickers`, `settings`, `administrators`, `payment-gateway`,
        `client-reference`, `discounts`, `notification-policy`, `agreements`.

- **Пациентское приложение (`/app`)**:
  - Обёрнуто в `PatientAuthProvider` + `AppLayout`.
  - Страницы:
    - `index` → `HomePage` (главная).
    - `/app/feed` → `FeedPage` (маркетинг/лента).
    - `/app/booking` → `BookingWizardPage` (мастер записи).
    - `/app/history` → `HistoryPage` (история записей).
    - `/app/chat` → `ChatPage` (личный чат).

- **Auth/результаты**:
  - `/login` — экран логина пациента (SMS‑код, OAuth).
  - `/oauth/result` — страница завершения OAuth‑флоу.
  - `/booking/success` — экран успешного бронирования/оплаты.

---

## 4. Управление состоянием и авторизацией

### 4.1. Пациентская auth‑модель

```1:68:d:\CURSOR\projects\dental_booking\frontend\src\contexts\PatientAuthContext.tsx
const TOKEN_KEY = "dental_booking_patient_token";
const PATIENT_ID_KEY = "dental_booking_patient_id";

interface PatientAuthState {
  accessToken: string | null;
  patientId: string | null;
}

...

export function PatientAuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<PatientAuthState>(readStored);

  const login = useCallback((token: string, patientId: string) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(PATIENT_ID_KEY, patientId);
    setState({ accessToken: token, patientId });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(PATIENT_ID_KEY);
    setState({ accessToken: null, patientId: null });
  }, []);
}
```

- Хранит JWT пациента и `patientId` в `localStorage`.
- Предоставляет хуки для логина/логаута и доступ к текущему состоянию.
- Используется:
  - В `LoginPage` / `OAuthResultPage` для установки токена.
  - В хуках запросов (`usePatientChat`, `usePatientBookings` и др.) для подстановки токена в `api.client`.

### 4.2. Админская клиника и бизнес‑лексикон

```23:71:d:\CURSOR\projects\dental_booking\frontend\src\contexts\AdminClinicContext.tsx
export function AdminClinicProvider({ children }: AdminClinicProviderProps) {
  const { data, isLoading, error } = useClinics();
  const [currentClinicId, setCurrentClinicId] = useState<string | null>(null);

  const clinics = data ?? [];

  useEffect(() => {
    if (!clinics.length) return;
    setCurrentClinicId((prev) => prev ?? clinics[0].id);
  }, [clinics]);

  return (
    <AdminClinicContext.Provider
      value={{
        clinics,
        currentClinicId,
        setCurrentClinicId,
        isLoading,
        error,
        businessLexicon:
          (clinics.find((c) => c.id === currentClinicId)?.business_lexicon as BusinessLexicon | undefined) ?? null,
      }}
    >
      {children}
    </AdminClinicContext.Provider>
  );
}
```

- Подтягивает список клиник через `useClinics()` (React Query) и выбирает текущую.
- Даёт доступ к:
  - Текущей клинике.
  - Бизнес‑лексикону (`BusinessLexicon`) — названия ролей и сущностей на языке конкретного бизнеса (клиника/салон/др.).
- Утилита `useBusinessLexicon()` даёт дефолтные подписи для стоматологии, если лексикон не задан.

### 4.3. HTTP‑клиент и обработка токенов

```7:152:d:\CURSOR\projects\dental_booking\frontend\src\api\client.ts
const BASE = "/api";
...
const needsAdminToken =
  (path.startsWith("/v1/admin") && !path.includes("/v1/admin/auth/login")) || path.startsWith("/v1/owner/");
const resolvedToken = token ?? (needsAdminToken ? getAdminToken() : null);
...
const isAdminOrOwnerUnauthorized =
  (path.includes("/v1/admin") && !path.includes("/v1/admin/auth/login")) || path.startsWith("/v1/owner/");
if (res.status === 401 && isAdminOrOwnerUnauthorized) {
  clearAdminToken();
  if (typeof window !== "undefined") {
    window.location.href = "/admin/login";
  }
  throw new Error("Требуется авторизация");
}
if (res.status === 401 && path.includes("/v1/patient/")) {
  clearPatientAuth();
  ...
  throw new Error(rawMessage);
}
```

- Базовый URL: `"/api"`, далее пути вида `"/v1/..."` → `"/api/v1/..."` (совпадает с префиксом backend).
- Для `/v1/admin/*` (кроме login) и `/v1/owner/*` автоматом подставляет админ‑токен из `localStorage`.
- Для `/v1/patient/*` токен передаётся явно из `PatientAuthContext`.
- На 401:
  - Для админа/owner:
    - Токен удаляется, выполняется redirect на `/admin/login`.
  - Для пациента:
    - Очищается auth, redirect на `/login`.
- Ошибки:
  - Для 4xx UI получает «сырой» текст из backend (важно для бизнес‑сообщений).
  - Для 5xx со стектрейсом текст заменяется на короткое сообщение про внутреннюю ошибку и необходимость проверки логов/миграций.

---

## 5. Структура модулей и страниц

### 5.1. Организация каталогов

- `frontend/src/App.tsx` — корневой роутер.
- `frontend/src/theme.ts` — дизайн‑система (цвета, типографика).
- `frontend/src/app/layouts/AppLayout.tsx` — layout пациента.
- `frontend/src/admin/layouts/AdminLayout.tsx` — layout админки.
- `frontend/src/admin/pages/*.tsx` — страницы админки.
- `frontend/src/app/pages/*.tsx` — страницы пациентского приложения.
- `frontend/src/api/client.ts` — HTTP‑клиент.
- `frontend/src/api/types.ts` — типы данных, синхронизированные с backend DTO.
- `frontend/src/hooks/*.ts` — React Query‑хуки и вспомогательные хуки.
- `frontend/src/contexts/*.tsx` — контексты (`PatientAuthContext`, `AdminClinicContext` и др.).
- `frontend/src/shared/ui/*.tsx` — переиспользуемые UI‑компоненты (`EmptyState`, `DataSkeleton`, `GlassModal` и др.).
- `frontend/src/pwa/registerPwa.ts` — регистрация PWA.
- `frontend/src/shared/ErrorBoundary.tsx` — error boundary всего UI.

### 5.2. Основные области функционала (по страницам и хукам)

- **Расписание и записи (админ)**:
  - Страницы:
    - `AdminBookingsPage`, `SchedulePage`, `AdminDoctorSchedulePage`.
  - Хуки:
    - `useAdminBookings` — CRUD записей и фильтрация.
    - `useDoctorSchedule`, `useDoctorScheduleAdmin`, `useAdminSchedule`.
    - `useDoctorScheduleConfig`.
  - UI:
    - Drag‑and‑drop слотов через `@dnd-kit`.

- **Пациентские записи и история**:
  - Страницы:
    - `BookingWizardPage`, `HistoryPage`, `BookingSuccessPage`, `HomePage`.
  - Хуки:
    - Хуки вокруг `/v1/patient/bookings` и `/v1/doctors/*/schedule` (в `useAuth`, `useDoctorSchedule`, `useServices*`).

- **Omnichannel и чат**:
  - Страницы:
    - `AdminOmniChatPage`, `AdminOmniChannelsPage`, `AdminOmniAiSettingsPage`, `AdminAiReportsPage`.
    - Пациентский `ChatPage`.
  - Хуки:
    - `useAdminOmniChat`, `useOwnerOmniChannels`, `useOwnerOmniAiSettings`, `useChatAi`.
    - `usePatientChat` (получение диалогов, сообщений, отправка/удаление/mark read).

- **Маркетинг и recall**:
  - Страницы:
    - `AdminMarketingPage`, `AdminRecallPage`, `FeedPage`, `AdminClientReferencePage`.
  - Хуки:
    - `useAdminRecall`, `useAdminMarketing`, `useClientReference`, `useAttentionFeed`, `useReports`.

- **Оплаты, предоплата и скидки**:
  - Страницы:
    - `AdminPrepaymentPage`, `AdminPaymentGatewayPage`, `AdminDiscountsPage`.
  - Хуки:
    - `useAdminPrepayment`, `useAdminPaymentGateway`, `useDiscounts`, `useServicesMutations` (редактирование цен/услуг).

- **Интеграции, стили, администраторы**:
  - Страницы:
    - `AdminIntegrationsPage`, `AdminStylingPage`, `AdminStickersPage`, `AdminAdministratorsPage`, `AdminAgreementsPage`, `AdminNotificationPolicyPage`, `AdminSettingsPage`.
  - Хуки:
    - Различные `useIntegrations`, `useStickers`, `useNotificationPolicy`, `useAgreements` и др., которые напрямую маппят REST‑эндпоинты backend.

---

## 6. PWA, стили и UX

- **PWA**:
  - Регистрация сервис‑воркера и манифеста в `registerPwa.ts` на основе `vite-plugin-pwa` (конфигурация в `vite.config.ts`).
  - Цель: офлайн‑кеширование, иконки и базовая PWA‑обвязка.

- **Темы и стили**:
  - Mantine‑тема описана в `theme.ts` и использует кастомные CSS‑переменные (`--bg-main`, `--bg-card`, `--text-main`, `--text-muted`, `--divider`).
  - Глобальные стили в `index.css`, PostCSS‑пайплайн через `postcss.config.cjs`.

- **Error handling в UI**:
  - `ErrorBoundary` оборачивает:
    - Весь `RouterProvider` в `App.tsx`.
    - Внутренний layout админки (`AdminLayout`) дополнительно.
  - Ошибки запросов HTTP показываются как user‑friendly сообщения на основе текста, нормализованного в `api/client.ts`.

---

## 7. Тестирование frontend

- **Скрипты** (из `frontend/package.json`):
  - `"dev": "vite"` — dev‑сервер.
  - `"build": "tsc -b && vite build"` — сборка TypeScript + Vite.
  - `"preview": "vite preview"` — предпросмотр собранного билда.
  - `"test": "vitest"` — юнит/компонентные тесты.
  - `"security:audit": "npm audit --production --audit-level=high"` — проверка зависимостей.

- **Стек тестов**:
  - Vitest + Testing Library (`@testing-library/react`, `@testing-library/jest-dom`) + `jsdom`.
  - Тесты живут в `frontend/src` рядом с компонентами или в специализированных тест‑файлах (по согласованному с @FRONTEND стилю).

---

## 8. Ключевые файлы frontend (для RAG и навигации)

- **Конфигурация и сборка**:
  - `frontend/package.json`
  - `frontend/vite.config.ts`
  - `frontend/postcss.config.cjs`
  - `frontend/tsconfig.json`, `frontend/tsconfig.node.json`

- **Вход и роутинг**:
  - `frontend/src/main.tsx`
  - `frontend/src/App.tsx`

- **HTTP‑клиент и типы**:
  - `frontend/src/api/client.ts`
  - `frontend/src/api/types.ts`

- **Контексты и auth**:
  - `frontend/src/contexts/PatientAuthContext.tsx`
  - `frontend/src/contexts/AdminClinicContext.tsx`
  - `frontend/src/admin/AdminAuthGuard.tsx`

- **Хуки данных**:
  - `frontend/src/hooks/index.ts`
  - `frontend/src/hooks/useAuth.ts`
  - `frontend/src/hooks/useAdminBookings.ts`
  - `frontend/src/hooks/useDoctorSchedule.ts`
  - `frontend/src/hooks/usePatientChat.ts`
  - `frontend/src/hooks/useOwnerOmniChannels.ts`
  - `frontend/src/hooks/useOwnerOmniAiSettings.ts`
  - `frontend/src/hooks/useAdminOmniChat.ts`
  - `frontend/src/hooks/useAdminPaymentGateway.ts`
  - `frontend/src/hooks/useAdminRecall.ts`, `useAdminMarketing.ts`, `useReports.ts` и др.

- **Страницы и layout‑ы**:
  - `frontend/src/app/layouts/AppLayout.tsx`
  - `frontend/src/app/pages/*.tsx`
  - `frontend/src/admin/layouts/AdminLayout.tsx`
  - `frontend/src/admin/pages/*.tsx`

- **PWA и общие компоненты**:
  - `frontend/src/pwa/registerPwa.ts`
  - `frontend/src/theme.ts`
  - `frontend/src/shared/ui/*.tsx`
  - `frontend/src/shared/ErrorBoundary.tsx`

Этот паспорт фиксирует фактическое состояние frontend‑части проекта по коду и конфигурации и предназначен как источник правды для разработки, ревью и RAG‑индексации.

