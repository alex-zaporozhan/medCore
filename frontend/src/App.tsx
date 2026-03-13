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
import AdminNotificationPolicyPage from "@/admin/pages/AdminNotificationPolicyPage";
import AdminAgreementsPage from "@/admin/pages/AdminAgreementsPage";
import AdminSettingsPage from "@/admin/pages/AdminSettingsPage";
import AdminPaymentGatewayPage from "@/admin/pages/AdminPaymentGatewayPage";
import AdminLoginPage from "@/admin/pages/AdminLoginPage";
import AdminAdministratorsPage from "@/admin/pages/AdminAdministratorsPage";
import AdminAuthGuard from "@/admin/AdminAuthGuard";
import { AdminClinicProvider } from "@/contexts/AdminClinicContext";
import SchedulePage from "@/admin/pages/SchedulePage";
import BookingSuccessPage from "@/app/pages/BookingSuccessPage";
import BookingWizardPage from "@/app/pages/BookingWizardPage";
import HistoryPage from "@/app/pages/HistoryPage";
import ChatPage from "@/app/pages/ChatPage";
import FeedPage from "@/app/pages/FeedPage";
import HomePage from "@/app/pages/HomePage";
import LoginPage from "@/app/pages/LoginPage";
import OAuthResultPage from "@/app/pages/OAuthResultPage";
import { Box, Button, Container, Paper, Stack, Text, Title } from "@mantine/core";
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
      }}
    >
      <Container size="sm">
        <Paper
          p="xl"
          radius="lg"
          shadow="sm"
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--divider)",
          }}
        >
          <Stack gap="xl">
            <Title order={1} style={{ color: "var(--text-main)" }}>
              Dental Booking
            </Title>
            <Text size="md" style={{ color: "var(--text-muted)" }}>
              Онлайн‑запись в стоматологию. Выберите раздел для входа.
            </Text>
            <Stack gap="md">
              <Button
                component={Link}
                to="/app"
                size="lg"
                variant="filled"
                color="brand"
                fullWidth
              >
                Приложение пациента
              </Button>
              <Button
                component={Link}
                to="/admin"
                size="lg"
                variant="light"
                color="gray"
                fullWidth
              >
                Админка
              </Button>
            </Stack>
          </Stack>
        </Paper>
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
        <Route path="attention" element={<AdminAttentionFeedPage />} />
        <Route path="reports" element={<AdminReportsPage />} />
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
