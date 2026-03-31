/**
 * Дерево маршрутов и зоны — техпаспорт §2; §7: не менять разделение `/admin` / `/app` и цепочки guard’ов
 * (`AdminAuthGuard`, `PatientAuthProvider` + `AppLayout`) без архитектурного эпика.
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
import AdminOmniVaultPage from "@/admin/pages/AdminOmniVaultPage";
import AdminStylingPage from "@/admin/pages/AdminStylingPage";
import AdminStickersPage from "@/admin/pages/AdminStickersPage";
import AdminClientReferencePage from "@/admin/pages/AdminClientReferencePage";
import AdminDiscountsPage from "@/admin/pages/AdminDiscountsPage";
import AdminFinancePage from "@/admin/pages/AdminFinancePage";
import AdminLoyaltyPage from "@/admin/pages/AdminLoyaltyPage";
import AdminFormsPage from "@/admin/pages/AdminFormsPage";
import AdminNotificationPolicyPage from "@/admin/pages/AdminNotificationPolicyPage";
import AdminAgreementsPage from "@/admin/pages/AdminAgreementsPage";
import AdminSettingsPage from "@/admin/pages/AdminSettingsPage";
import AdminRightsPoliciesPage from "@/admin/pages/AdminRightsPoliciesPage";
import AdminPaymentGatewayPage from "@/admin/pages/AdminPaymentGatewayPage";
import AdminLoginPage from "@/admin/pages/AdminLoginPage";
import AdminAdministratorsPage from "@/admin/pages/AdminAdministratorsPage";
import AdminSalesPipelinePage from "@/admin/pages/AdminSalesPipelinePage";
import AdminTasksPage from "@/admin/pages/AdminTasksPage";
import AdminStaffChatPage from "@/admin/pages/AdminStaffChatPage";
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
import LoginPage from "@/app/pages/LoginPage";
import OAuthResultPage from "@/app/pages/OAuthResultPage";
import FormsPage from "@/app/pages/FormsPage";
import {
  ADMIN_SHELL_ROUTE_SEGMENTS,
  PATIENT_APP_ROUTE_SEGMENTS,
  ROUTE_PATHS,
  type AdminShellSegment,
  type PatientAppSegment,
} from "@/routePaths";
import { isAdminSegmentBlockedInBox } from "@/config/edition";
import { Box, Button, Container, Grid, Paper, Stack, Text, Title } from "@mantine/core";
import { createElement, type ComponentType } from "react";
import {
  createBrowserRouter,
  Link,
  Navigate,
  RouterProvider,
  Route,
  createRoutesFromElements,
} from "react-router-dom";

const ADMIN_SHELL_PAGE_BY_SEGMENT: Record<AdminShellSegment, ComponentType> = {
  "staff-chat": AdminStaffChatPage,
  calendar: AdminStaffCalendarPage,
  knowledge: AdminKnowledgePage,
  clinics: AdminClinicsPage,
  services: AdminServicesPage,
  schedule: SchedulePage,
  tasks: AdminTasksPage,
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
  "omni-vault": AdminOmniVaultPage,
  styling: AdminStylingPage,
  stickers: AdminStickersPage,
  settings: AdminSettingsPage,
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
  if (isAdminSegmentBlockedInBox(seg)) {
    return <Navigate to={ROUTE_PATHS.admin.dashboard} replace />;
  }
  const Page = ADMIN_SHELL_PAGE_BY_SEGMENT[seg];
  return <Page />;
}

function LandingPage() {
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
                      to={ROUTE_PATHS.patient.home}
                      size="lg"
                      variant="filled"
                      color="teal"
                    >
                      Приложение пациента
                    </Button>
                    <Button
                      component={Link}
                      to={ROUTE_PATHS.admin.dashboard}
                      size="md"
                      variant="outline"
                      color="dark"
                    >
                      Войти в Business OS (админка)
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
        </Stack>
      </Container>
    </Box>
  );
}

const router = createBrowserRouter(
  createRoutesFromElements(
    <>
      <Route path={ROUTE_PATHS.marketing.landing} element={<LandingPage />} />
      <Route path={ROUTE_PATHS.admin.dashboard} element={<AdminAuthGuard />}>
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
          {ADMIN_SHELL_ROUTE_SEGMENTS.map((seg) => (
            <Route
              key={seg}
              path={seg}
              element={<AdminShellSegmentPage seg={seg} />}
            />
          ))}
        </Route>
      </Route>
      <Route
        path={ROUTE_PATHS.other.login}
        element={
          <PatientAuthProvider>
            <LoginPage />
          </PatientAuthProvider>
        }
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
