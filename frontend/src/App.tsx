import { ErrorBoundary } from "@/shared/ErrorBoundary";
import { PatientAuthProvider } from "@/contexts/PatientAuthContext";
import AdminLayout from "@/admin/layouts/AdminLayout";
import AppLayout from "@/app/layouts/AppLayout";
import AdminBookingsPage from "@/admin/pages/AdminBookingsPage";
import AdminDashboardPage from "@/admin/pages/AdminDashboardPage";
import AdminDoctorsPage from "@/admin/pages/AdminDoctorsPage";
import AdminPatientsPage from "@/admin/pages/AdminPatientsPage";
import AdminReportsPage from "@/admin/pages/AdminReportsPage";
import AdminAttentionFeedPage from "@/admin/pages/AdminAttentionFeedPage";
import AdminClinicsPage from "@/admin/pages/AdminClinicsPage";
import AdminServicesPage from "@/admin/pages/AdminServicesPage";
import AdminPrepaymentPage from "@/admin/pages/AdminPrepaymentPage";
import AdminWaitlistPage from "@/admin/pages/AdminWaitlistPage";
import AdminRecallPage from "@/admin/pages/AdminRecallPage";
import AdminMarketingPage from "@/admin/pages/AdminMarketingPage";
import AdminDoctorSchedulePage from "@/admin/pages/AdminDoctorSchedulePage";
import AdminOmniChatPage from "@/admin/pages/AdminOmniChatPage";
import AdminOmniAiSettingsPage from "@/admin/pages/AdminOmniAiSettingsPage";
import AdminChannelsPage from "@/admin/pages/AdminChannelsPage";
import AdminOmniChannelsPage from "@/admin/pages/AdminOmniChannelsPage";
import AdminIntegrationsPage from "@/admin/pages/AdminIntegrationsPage";
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
import AdminPaymentGatewayPage from "@/admin/pages/AdminPaymentGatewayPage";
import AdminLoginPage from "@/admin/pages/AdminLoginPage";
import AdminAdministratorsPage from "@/admin/pages/AdminAdministratorsPage";
import AdminSalesPipelinePage from "@/admin/pages/AdminSalesPipelinePage";
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
import LoginPage from "@/app/pages/LoginPage";
import OAuthResultPage from "@/app/pages/OAuthResultPage";
import FormsPage from "@/app/pages/FormsPage";
import { Box, Button, Container, Grid, Paper, Stack, Text, Title } from "@mantine/core";
import {
  createBrowserRouter,
  Link,
  RouterProvider,
  Route,
  createRoutesFromElements,
} from "react-router-dom";

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
            radius="lg"
            shadow="sm"
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
                      to="/app"
                      size="lg"
                      variant="filled"
                      color="brand"
                    >
                      Приложение пациента
                    </Button>
                    <Button
                      component={Link}
                      to="/admin"
                      size="md"
                      variant="light"
                      color="gray"
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
            radius="lg"
            shadow="sm"
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
        <Route path="clinics" element={<AdminClinicsPage />} />
        <Route path="services" element={<AdminServicesPage />} />
        <Route path="schedule" element={<SchedulePage />} />
        <Route path="bookings" element={<AdminBookingsPage />} />
        <Route path="prepayment" element={<AdminPrepaymentPage />} />
        <Route path="waitlist" element={<AdminWaitlistPage />} />
        <Route path="recall" element={<AdminRecallPage />} />
        <Route path="marketing" element={<AdminMarketingPage />} />
        <Route path="sales" element={<AdminSalesPipelinePage />} />
        <Route path="attention" element={<AdminAttentionFeedPage />} />
        <Route path="reports" element={<AdminReportsPage />} />
        <Route path="finance" element={<AdminFinancePage />} />
        <Route path="loyalty" element={<AdminLoyaltyPage />} />
        <Route path="forms" element={<AdminFormsPage />} />
        <Route path="doctors" element={<AdminDoctorsPage />} />
        <Route path="doctor-schedule" element={<AdminDoctorSchedulePage />} />
        <Route path="patients" element={<AdminPatientsPage />} />
        <Route path="omni-chat" element={<AdminOmniChatPage />} />
        <Route path="omni-channels" element={<AdminOmniChannelsPage />} />
        <Route path="omni-ai-settings" element={<AdminOmniAiSettingsPage />} />
        <Route path="channels" element={<AdminChannelsPage />} />
        <Route path="integrations" element={<AdminIntegrationsPage />} />
        <Route path="styling" element={<AdminStylingPage />} />
        <Route path="stickers" element={<AdminStickersPage />} />
        <Route path="settings" element={<AdminSettingsPage />} />
        <Route path="administrators" element={<AdminAdministratorsPage />} />
        <Route path="payment-gateway" element={<AdminPaymentGatewayPage />} />
        <Route path="client-reference" element={<AdminClientReferencePage />} />
        <Route path="discounts" element={<AdminDiscountsPage />} />
        <Route path="notification-policy" element={<AdminNotificationPolicyPage />} />
        <Route path="agreements" element={<AdminAgreementsPage />} />
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
        <Route path="loyalty" element={<LoyaltyPage />} />
        <Route path="forms" element={<FormsPage />} />
        <Route path="chat" element={<ChatPage />} />
      </Route>
      <Route path="/booking/success" element={<BookingSuccessPage />} />
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
