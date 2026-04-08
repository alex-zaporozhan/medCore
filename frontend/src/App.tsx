/**
 * Дерево маршрутов: маркетинг `/`, вход клиники `/admin/login`, основатель `/platform/login`,
 * пациент только `/c/:clinicSlug/sign-in`, legacy `/sign-in` → редиректы.
 */
import { ErrorBoundary } from "@/shared/ErrorBoundary";
import { PatientAuthProvider } from "@/contexts/PatientAuthContext";
import AdminLayout from "@/admin/layouts/AdminLayout";
import AppLayout from "@/app/layouts/AppLayout";
import AdminBookingsPage from "@/admin/pages/AdminBookingsPage";
import AdminDashboardPage from "@/admin/pages/AdminDashboardPage";
import AdminDoctorsPage from "@/admin/pages/AdminDoctorsPage";
import AdminPatientsPage from "@/admin/pages/AdminPatientsPage";
import AdminReportsPage from "@/admin/pages/AdminReportsPage";
import AdminClinicsPage from "@/admin/pages/AdminClinicsPage";
import AdminServicesPage from "@/admin/pages/AdminServicesPage";
import AdminPrepaymentPage from "@/admin/pages/AdminPrepaymentPage";
import AdminWaitlistPage from "@/admin/pages/AdminWaitlistPage";
import AdminRecallPage from "@/admin/pages/AdminRecallPage";
import AdminMarketingPage from "@/admin/pages/AdminMarketingPage";
import AdminRetentionPage from "@/admin/pages/AdminRetentionPage";
import AdminDoctorSchedulePage from "@/admin/pages/AdminDoctorSchedulePage";
import AdminOmniChatPage from "@/admin/pages/AdminOmniChatPage";
import AdminOmniAiSettingsPage from "@/admin/pages/AdminOmniAiSettingsPage";
import AdminChannelsPage from "@/admin/pages/AdminChannelsPage";
import AdminOmniChannelsPage from "@/admin/pages/AdminOmniChannelsPage";
import AdminIntegrationsPage from "@/admin/pages/AdminIntegrationsPage";
import AdminEmbedPage from "@/admin/pages/AdminEmbedPage";
import AdminRagKbPage from "@/admin/pages/AdminRagKbPage";
import AdminDataExportPage from "@/admin/pages/AdminDataExportPage";
import AdminOmniVaultPage from "@/admin/pages/AdminOmniVaultPage";
import AdminStylingPage from "@/admin/pages/AdminStylingPage";
import AdminStickersPage from "@/admin/pages/AdminStickersPage";
import AdminClientReferencePage from "@/admin/pages/AdminClientReferencePage";
import AdminDiscountsPage from "@/admin/pages/AdminDiscountsPage";
import AdminFinancePage from "@/admin/pages/AdminFinancePage";
import AdminCommercePage from "@/admin/pages/AdminCommercePage";
import AdminLoyaltyPage from "@/admin/pages/AdminLoyaltyPage";
import AdminFormsPage from "@/admin/pages/AdminFormsPage";
import AdminNotificationPolicyPage from "@/admin/pages/AdminNotificationPolicyPage";
import AdminAgreementsPage from "@/admin/pages/AdminAgreementsPage";
import AdminSettingsPage from "@/admin/pages/AdminSettingsPage";
import AdminSubscriptionPage from "@/admin/pages/AdminSubscriptionPage";
import AdminRightsPoliciesPage from "@/admin/pages/AdminRightsPoliciesPage";
import AdminPaymentGatewayPage from "@/admin/pages/AdminPaymentGatewayPage";
import AdminAdministratorsPage from "@/admin/pages/AdminAdministratorsPage";
import AdminSalesPipelinePage from "@/admin/pages/AdminSalesPipelinePage";
import AdminTasksPage from "@/admin/pages/AdminTasksPage";
import AdminLeadsLogPage from "@/admin/pages/AdminLeadsLogPage";
import AdminTaskDetailsPage from "@/admin/pages/AdminTaskDetailsPage";
import AdminStaffChatPage from "@/admin/pages/AdminStaffChatPage";
import AdminStaffCabinetPage from "@/admin/pages/AdminStaffCabinetPage";
import AdminStaffCalendarPage from "@/admin/pages/AdminStaffCalendarPage";
import AdminKnowledgePage from "@/admin/pages/AdminKnowledgePage";
import AdminEmergencyNotificationsPage from "@/admin/pages/AdminEmergencyNotificationsPage";
import AdminAuthGuard from "@/admin/AdminAuthGuard";
import { AdminClinicProvider } from "@/contexts/AdminClinicContext";
import SchedulePage from "@/admin/pages/SchedulePage";
import BookingSuccessPage from "@/app/pages/BookingSuccessPage";
import BookingWizardPage from "@/app/pages/BookingWizardPage";
import HistoryPage from "@/app/pages/HistoryPage";
import LoyaltyPage from "@/app/pages/LoyaltyPage";
import ChatPage from "@/app/pages/ChatPage";
import FeedPage from "@/app/pages/FeedPage";
import HomePage from "@/app/pages/HomePage";
import ProfilePage from "@/app/pages/ProfilePage";
import ClinicSignInPage from "@/auth/ClinicSignInPage";
import LegacySignInRedirect from "@/auth/LegacySignInRedirect";
import PatientSignInPage from "@/auth/PatientSignInPage";
import OAuthResultPage from "@/app/pages/OAuthResultPage";
import FormsPage from "@/app/pages/FormsPage";
import PublicDoctorProfilePage from "@/marketing/pages/PublicDoctorProfilePage";
import LegalPrivacyPage from "@/marketing/pages/LegalPrivacyPage";
import LegalTermsPage from "@/marketing/pages/LegalTermsPage";
import PlatformFounderLayout from "@/marketing/layouts/PlatformFounderLayout";
import PlatformFounderDashboardPage from "@/marketing/pages/PlatformFounderDashboardPage";
import PlatformFounderProvisionQueuePage from "@/marketing/pages/PlatformFounderProvisionQueuePage";
import PlatformFounderLoginPage from "@/marketing/pages/PlatformFounderLoginPage";
import PlatformFounderMfaPage from "@/marketing/pages/PlatformFounderMfaPage";
import PricingPage from "@/marketing/pages/PricingPage";
import SignupPage from "@/marketing/pages/SignupPage";
import { PatientEntryBoundary } from "@/contexts/PatientEntryContext";
import {
  ADMIN_SHELL_ROUTE_SEGMENTS,
  PATIENT_APP_ROUTE_SEGMENTS,
  ROUTE_PATHS,
  type AdminShellSegment,
  type PatientAppSegment,
} from "@/routePaths";
import { isAdminSegmentBlockedInBox } from "@/config/edition";
import {
  adminShellSegmentEntitlementKey,
  isAdminSegmentBlockedByEntitlements,
} from "@/shared/adminEntitlementNav";
import { useAdminSession } from "@/hooks/useAdminSession";
import {
  Alert,
  Anchor,
  Box,
  Button,
  Center,
  Container,
  Grid,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { createElement, type ComponentType, useMemo, useState } from "react";
import {
  createBrowserRouter,
  createRoutesFromElements,
  createSearchParams,
  Link,
  Navigate,
  Route,
  RouterProvider,
  useNavigate,
  useSearchParams,
} from "react-router-dom";

const ADMIN_SHELL_PAGE_BY_SEGMENT: Record<AdminShellSegment, ComponentType> = {
  "staff-chat": AdminStaffChatPage,
  me: AdminStaffCabinetPage,
  calendar: AdminStaffCalendarPage,
  knowledge: AdminKnowledgePage,
  clinics: AdminClinicsPage,
  services: AdminServicesPage,
  schedule: SchedulePage,
  tasks: AdminTasksPage,
  "leads-log": AdminLeadsLogPage,
  bookings: AdminBookingsPage,
  prepayment: AdminPrepaymentPage,
  waitlist: AdminWaitlistPage,
  recall: AdminRecallPage,
  marketing: AdminMarketingPage,
  retention: AdminRetentionPage,
  sales: AdminSalesPipelinePage,
  attention: AdminEmergencyNotificationsPage,
  reports: AdminReportsPage,
  finance: AdminFinancePage,
  commerce: AdminCommercePage,
  loyalty: AdminLoyaltyPage,
  forms: AdminFormsPage,
  doctors: AdminDoctorsPage,
  "doctor-schedule": AdminDoctorSchedulePage,
  patients: AdminPatientsPage,
  "omni-chat": AdminOmniChatPage,
  "omni-channels": AdminOmniChannelsPage,
  "omni-ai-settings": AdminOmniAiSettingsPage,
  channels: AdminChannelsPage,
  integrations: AdminIntegrationsPage,
  embed: AdminEmbedPage,
  "rag-kb": AdminRagKbPage,
  "data-export": AdminDataExportPage,
  "omni-vault": AdminOmniVaultPage,
  styling: AdminStylingPage,
  stickers: AdminStickersPage,
  settings: AdminSettingsPage,
  subscription: AdminSubscriptionPage,
  administrators: AdminAdministratorsPage,
  "payment-gateway": AdminPaymentGatewayPage,
  "client-reference": AdminClientReferencePage,
  discounts: AdminDiscountsPage,
  "notification-policy": AdminNotificationPolicyPage,
  agreements: AdminAgreementsPage,
  "rights-policies": AdminRightsPoliciesPage,
};

const PATIENT_APP_PAGE_BY_SEGMENT: Record<PatientAppSegment, ComponentType> = {
  feed: FeedPage,
  booking: BookingWizardPage,
  history: HistoryPage,
  loyalty: LoyaltyPage,
  forms: FormsPage,
  chat: ChatPage,
  profile: ProfilePage,
};

function AdminShellSegmentPage({ seg }: { seg: AdminShellSegment }) {
  const { data: adminSession, isLoading, isFetching } = useAdminSession();
  if (isAdminSegmentBlockedInBox(seg)) {
    return <Navigate to={ROUTE_PATHS.admin.dashboard} replace />;
  }
  const segmentEntitlementKey = adminShellSegmentEntitlementKey(seg);
  if (
    segmentEntitlementKey &&
    adminSession === undefined &&
    (isLoading || isFetching)
  ) {
    return (
      <Center h="min(50vh, 320px)">
        <Loader size="md" />
      </Center>
    );
  }
  if (
    isAdminSegmentBlockedByEntitlements(
      seg,
      adminSession?.entitlement_enforced ?? false,
      adminSession?.entitlement_keys,
    )
  ) {
    return <Navigate to={ROUTE_PATHS.admin.dashboard} replace />;
  }
  const Page = ADMIN_SHELL_PAGE_BY_SEGMENT[seg];
  return <Page />;
}

function LandingPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [patientSlug, setPatientSlug] = useState("");

  const patientEntryHint = useMemo(() => {
    const v = searchParams.get("patientEntry");
    if (v === "need-clinic") {
      return "Войдите по ссылке вашей клиники или укажите адрес клиники ниже (как в ссылке …/c/адрес-клиники/…).";
    }
    if (v === "patient-url-needs-clinic-slug") {
      return "В ссылке для входа пациента должен быть адрес клиники: /c/ваш-slug/sign-in (три части пути после домена), а не /c/sign-in.";
    }
    if (v === "session-expired") {
      return "Сессия истекла. Войдите снова по ссылке клиники.";
    }
    if (v === "oauth-cancelled" || v === "oauth-error") {
      return "Вход через соцсеть прерван или не удался. Используйте ссылку клиники и вход по телефону.";
    }
    return null;
  }, [searchParams]);

  const goPatientBySlug = () => {
    const raw = patientSlug.trim().replace(/^\/+|\/+$/g, "");
    if (!raw) return;
    const slug = raw.replace(/^c\//i, "").split("/")[0]?.trim();
    if (!slug) return;
    navigate(`/c/${encodeURIComponent(slug)}/sign-in`);
  };

  return (
    <Box
      style={{
        minHeight: "100vh",
        background: "var(--bg-main)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 16px",
      }}
    >
      <Container size="lg">
        <Stack gap="xl">
          {patientEntryHint ? (
            <Alert color="teal" variant="light" title="Вход для пациентов">
              {patientEntryHint}
            </Alert>
          ) : null}
          <Paper
            p="xl"
            radius="md"
            shadow="none"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--divider)",
            }}
          >
            <Grid gutter="xl" align="center">
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Stack gap="md">
                  <Text size="xs" fw={600} c="var(--text-muted)" tt="uppercase">
                    Business OS для клиник
                  </Text>
                  <Title order={1} style={{ color: "var(--text-main)" }}>
                    Dental Booking Business OS
                  </Title>
                  <Text size="md" style={{ color: "var(--text-muted)" }}>
                    Одна операционная система для записи, чатов, CRM, AI‑агента, финансов и
                    лояльности. Пациенту — онлайн‑сервисы, клинике — управляемый рост.
                  </Text>
                  <Stack gap="sm">
                    <Button
                      component={Link}
                      to={{
                        pathname: ROUTE_PATHS.admin.login,
                        search: `?${createSearchParams({
                          returnTo: ROUTE_PATHS.admin.dashboard,
                        }).toString()}`,
                      }}
                      size="lg"
                      variant="filled"
                      color="dark"
                    >
                      Войти в Business OS (клиника)
                    </Button>
                    <Text size="sm" fw={600} c="dimmed">
                      Пациентам
                    </Text>
                    <Text size="xs" c="dimmed">
                      У каждой клиники свой адрес в ссылке. Вставьте адрес из приглашения (поддомен / путь после{" "}
                      <Text span ff="monospace">
                        /c/
                      </Text>
                      ).
                    </Text>
                    <Group gap="xs" align="flex-end" wrap="nowrap">
                      <TextInput
                        flex={1}
                        label="Адрес клиники"
                        placeholder="например demo-clinic"
                        value={patientSlug}
                        onChange={(e) => setPatientSlug(e.currentTarget.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") goPatientBySlug();
                        }}
                      />
                      <Button variant="filled" color="teal" onClick={goPatientBySlug}>
                        Войти
                      </Button>
                    </Group>
                    <Button component={Link} to={ROUTE_PATHS.marketing.signup} size="md" variant="light">
                      Подключить клинику (тариф и оплата)
                    </Button>
                    <Button component={Link} to={ROUTE_PATHS.marketing.pricing} size="md" variant="light">
                      Смотреть тарифы
                    </Button>
                  </Stack>
                </Stack>
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Box
                  className="app-shell-card"
                  style={{
                    padding: 16,
                  }}
                >
                  <Stack gap="sm">
                    <Text size="sm" fw={600} c="var(--text-muted)">
                      Как выглядит работа
                    </Text>
                    <Text size="sm" c="dimmed">
                      Пример рабочего дня: оператор видит записи, чаты и задачи в едином
                      трёхколоночном окне — слева пациенты, по центру диалоги, справа контекст
                      CRM и AI‑агента.
                    </Text>
                  </Stack>
                </Box>
              </Grid.Col>
            </Grid>
          </Paper>

          <Paper
            p="xl"
            radius="md"
            shadow="none"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--divider)",
            }}
          >
            <Stack gap="md">
              <Title order={3} style={{ color: "var(--text-main)" }}>
                Модули Business OS
              </Title>
              <Grid gutter="md">
                <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
                  <Stack gap={4}>
                    <Text fw={600}>AI Agent</Text>
                    <Text size="sm" c="dimmed">
                      Отвечает на входящие обращения, помогает операторам и создаёт задачи.
                    </Text>
                  </Stack>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
                  <Stack gap={4}>
                    <Text fw={600}>CRM & Sales</Text>
                    <Text size="sm" c="dimmed">
                      Воронка продаж с лидами из чатов, маркетинга и сайта.
                    </Text>
                  </Stack>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
                  <Stack gap={4}>
                    <Text fw={600}>Finance & ERP</Text>
                    <Text size="sm" c="dimmed">
                      Кассы, выручка, склад и зарплаты в одной панели.
                    </Text>
                  </Stack>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
                  <Stack gap={4}>
                    <Text fw={600}>Tasks</Text>
                    <Text size="sm" c="dimmed">
                      Единый список задач по пациентам, каналам и финансам.
                    </Text>
                  </Stack>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
                  <Stack gap={4}>
                    <Text fw={600}>Loyalty</Text>
                    <Text size="sm" c="dimmed">
                      Баллы, абонементы и удержание пациентов.
                    </Text>
                  </Stack>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
                  <Stack gap={4}>
                    <Text fw={600}>Paperless & Attribution</Text>
                    <Text size="sm" c="dimmed">
                      Цифровые формы, согласия и сквозная аналитика маркетинга.
                    </Text>
                  </Stack>
                </Grid.Col>
              </Grid>
            </Stack>
          </Paper>

          <Group gap="lg" justify="center" wrap="wrap" py="md">
            <Anchor component={Link} size="sm" c="dimmed" to={ROUTE_PATHS.marketing.pricing}>
              Тарифы
            </Anchor>
            <Anchor component={Link} size="sm" c="dimmed" to={ROUTE_PATHS.marketing.legalPrivacy}>
              Конфиденциальность
            </Anchor>
            <Anchor component={Link} size="sm" c="dimmed" to={ROUTE_PATHS.marketing.legalTerms}>
              Условия использования
            </Anchor>
            <Anchor component={Link} size="sm" c="dimmed" to={ROUTE_PATHS.platform.provisionQueue}>
              Очередь провижининга
            </Anchor>
          </Group>
        </Stack>
      </Container>
    </Box>
  );
}

const router = createBrowserRouter(
  createRoutesFromElements(
    <>
      <Route path={ROUTE_PATHS.marketing.landing} element={<LandingPage />} />
      <Route path={ROUTE_PATHS.marketing.pricing} element={<PricingPage />} />
      <Route path={ROUTE_PATHS.marketing.signup} element={<SignupPage />} />
      <Route path={ROUTE_PATHS.marketing.legalPrivacy} element={<LegalPrivacyPage />} />
      <Route path={ROUTE_PATHS.marketing.legalTerms} element={<LegalTermsPage />} />
      <Route path={ROUTE_PATHS.platform.loginMfa} element={<PlatformFounderMfaPage />} />
      <Route path={ROUTE_PATHS.platform.login} element={<PlatformFounderLoginPage />} />
      <Route path="/platform" element={<PlatformFounderLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<PlatformFounderDashboardPage />} />
        <Route path="provision-queue" element={<PlatformFounderProvisionQueuePage />} />
      </Route>
      <Route path="/:clinicSlug/doctors/:doctorSlug" element={<PublicDoctorProfilePage />} />
      <Route path={ROUTE_PATHS.admin.dashboard} element={<AdminAuthGuard />}>
        <Route path="login" element={<ClinicSignInPage />} />
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
          <Route path="tasks/:taskId" element={<AdminTaskDetailsPage />} />
          {ADMIN_SHELL_ROUTE_SEGMENTS.map((seg) => (
            <Route
              key={seg}
              path={seg}
              element={<AdminShellSegmentPage seg={seg} />}
            />
          ))}
        </Route>
      </Route>
      <Route path={ROUTE_PATHS.other.signIn} element={<LegacySignInRedirect />} />
      <Route
        path={ROUTE_PATHS.other.login}
        element={<Navigate to={`${ROUTE_PATHS.marketing.landing}?patientEntry=need-clinic`} replace />}
      />
      <Route
        path={ROUTE_PATHS.other.oauthResult}
        element={
          <PatientAuthProvider>
            <OAuthResultPage />
          </PatientAuthProvider>
        }
      />
      <Route
        path={ROUTE_PATHS.patient.home}
        element={
          <PatientAuthProvider>
            <AppLayout />
          </PatientAuthProvider>
        }
      >
        <Route index element={<HomePage />} />
        {PATIENT_APP_ROUTE_SEGMENTS.map((seg) => (
          <Route
            key={seg}
            path={seg}
            element={createElement(PATIENT_APP_PAGE_BY_SEGMENT[seg])}
          />
        ))}
      </Route>
      {/**
       * Без этого `/c/sign-in` матчится как `/c/:clinicSlug` с clinicSlug=`sign-in`, а вложенный `sign-in`
       * ждёт путь `/c/…/sign-in/sign-in` — Outlet пустой (белый экран).
       */}
      <Route
        path="/c/sign-in"
        element={
          <Navigate
            to={`${ROUTE_PATHS.marketing.landing}?patientEntry=patient-url-needs-clinic-slug`}
            replace
          />
        }
      />
      <Route path="/c/:clinicSlug" element={<PatientEntryBoundary />}>
        {/** `/c/demo` → `/c/demo/sign-in`, иначе только родитель без дочернего — пустой Outlet */}
        <Route
          index
          element={<Navigate to="sign-in" replace />}
        />
        <Route
          path="sign-in"
          element={
            <PatientAuthProvider>
              <PatientSignInPage />
            </PatientAuthProvider>
          }
        />
        <Route
          path="app"
          element={
            <PatientAuthProvider>
              <AppLayout />
            </PatientAuthProvider>
          }
        >
          <Route index element={<HomePage />} />
          {PATIENT_APP_ROUTE_SEGMENTS.map((seg) => (
            <Route
              key={`c-${seg}`}
              path={seg}
              element={createElement(PATIENT_APP_PAGE_BY_SEGMENT[seg])}
            />
          ))}
        </Route>
      </Route>
      <Route path={ROUTE_PATHS.other.bookingSuccess} element={<BookingSuccessPage />} />
    </>
  ),
  { future: { v7_relativeSplatPath: true } }
);

export default function App() {
  return (
    <ErrorBoundary>
      <RouterProvider router={router} future={{ v7_startTransition: true }} />
    </ErrorBoundary>
  );
}
