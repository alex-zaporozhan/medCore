/**
 * Дерево маршрутов: маркетинг `/`, публичный вход `/login`, клиника `/admin/login`, основатель `/platform/login`,
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
import StorePage from "@/app/pages/StorePage";
import ClinicSignInPage from "@/auth/ClinicSignInPage";
import LegacySignInRedirect from "@/auth/LegacySignInRedirect";
import PatientSignInPage from "@/auth/PatientSignInPage";
import OAuthResultPage from "@/app/pages/OAuthResultPage";
import FormsPage from "@/app/pages/FormsPage";
import PublicDoctorProfilePage from "@/marketing/pages/PublicDoctorProfilePage";
import LegalPrivacyPage from "@/marketing/pages/LegalPrivacyPage";
import LegalTermsPage from "@/marketing/pages/LegalTermsPage";
import PlatformFounderLayout from "@/marketing/layouts/PlatformFounderLayout";
import PlatformFounderLoginPage from "@/marketing/pages/PlatformFounderLoginPage";
import PlatformFounderMfaPage from "@/marketing/pages/PlatformFounderMfaPage";
import MarketingLandingPage from "@/marketing/pages/MarketingLandingPage";
import MarketingSandboxPage from "@/marketing/pages/MarketingSandboxPage";
import PricingPage from "@/marketing/pages/PricingPage";
import PublicLoginPage from "@/marketing/pages/PublicLoginPage";
import SignupPage from "@/marketing/pages/SignupPage";
import PlatformOwnerInviteAcceptPage from "@/marketing/pages/PlatformOwnerInviteAcceptPage";
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
import { Center, Loader } from "@mantine/core";
import { createElement, lazy, Suspense, type ComponentType } from "react";
import {
  createBrowserRouter,
  createRoutesFromElements,
  Navigate,
  Route,
  RouterProvider,
} from "react-router-dom";

const PlatformFounderDashboardPage = lazy(() => import("@/marketing/pages/PlatformFounderDashboardPage"));
const PlatformFounderProvisionQueuePage = lazy(() => import("@/marketing/pages/PlatformFounderProvisionQueuePage"));
const PlatformFounderEnterpriseLeadsPage = lazy(() => import("@/marketing/pages/PlatformFounderEnterpriseLeadsPage"));

function PlatformFounderLazyFallback() {
  return (
    <Center mih={240}>
      <Loader size="md" />
    </Center>
  );
}

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
  store: StorePage,
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

const router = createBrowserRouter(
  createRoutesFromElements(
    <>
      <Route path={ROUTE_PATHS.marketing.landing} element={<MarketingLandingPage />} />
      <Route path={ROUTE_PATHS.marketing.sandbox} element={<MarketingSandboxPage />} />
      <Route path={ROUTE_PATHS.marketing.pricing} element={<PricingPage />} />
      <Route path={ROUTE_PATHS.marketing.ownerInviteAccept} element={<PlatformOwnerInviteAcceptPage />} />
      <Route path={ROUTE_PATHS.marketing.signup} element={<SignupPage />} />
      <Route path={ROUTE_PATHS.marketing.legalPrivacy} element={<LegalPrivacyPage />} />
      <Route path={ROUTE_PATHS.marketing.legalTerms} element={<LegalTermsPage />} />
      <Route path={ROUTE_PATHS.platform.loginMfa} element={<PlatformFounderMfaPage />} />
      <Route path={ROUTE_PATHS.platform.login} element={<PlatformFounderLoginPage />} />
      <Route path="/platform" element={<PlatformFounderLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route
          path="dashboard"
          element={
            <Suspense fallback={<PlatformFounderLazyFallback />}>
              <PlatformFounderDashboardPage />
            </Suspense>
          }
        />
        <Route
          path="provision-queue"
          element={
            <Suspense fallback={<PlatformFounderLazyFallback />}>
              <PlatformFounderProvisionQueuePage />
            </Suspense>
          }
        />
        <Route
          path="leads"
          element={
            <Suspense fallback={<PlatformFounderLazyFallback />}>
              <PlatformFounderEnterpriseLeadsPage />
            </Suspense>
          }
        />
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
      <Route path={ROUTE_PATHS.other.login} element={<PublicLoginPage />} />
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
            to={`${ROUTE_PATHS.other.login}?patientEntry=patient-url-needs-clinic-slug`}
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
  /**
   * React Router 7: former v7_* future flags are the default (startTransition,
   * relative splat paths). There are no `path="*"` splats in this tree; keep it that way
   * or re-read RR7 splat semantics before adding one.
   */
);

export default function App() {
  return (
    <ErrorBoundary>
      <RouterProvider router={router} />
    </ErrorBoundary>
  );
}
