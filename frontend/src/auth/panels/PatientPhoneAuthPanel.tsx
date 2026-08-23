import { usePatientAuth } from "@/contexts/PatientAuthContext";
import { usePatientEntry } from "@/contexts/PatientEntryContext";
import { useAgreement, useSendCode, useVerifyCode } from "@/hooks/useAuth";
import {
  Alert,
  Anchor,
  Button,
  Checkbox,
  Group,
  Modal,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useMemo, useState } from "react";
import { API_BASE, ApiErrorWithCode } from "@/api/client";
import { getCurrentUtm } from "@/shared/utmTracking";
import { SEMANTIC } from "@/shared/semanticUi";
import { ROUTE_PATHS } from "@/routePaths";
import { safeAuthReturnTo } from "@/auth/signInReturnTo";
import { useTranslation } from "react-i18next";

const EMPTY_DB_MESSAGE = "В базе данных нет ни одной клиники";

export function PatientPhoneAuthPanel() {
  const { t } = useTranslation("patient");
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { clinicSlug } = usePatientEntry();
  const oauthStartQuery = useMemo(() => {
    const redirectPath = clinicSlug ? `/c/${clinicSlug}/app` : ROUTE_PATHS.patient.home;
    const p = new URLSearchParams({ redirect: redirectPath });
    if (clinicSlug) p.set("clinic_slug", clinicSlug);
    return p.toString();
  }, [clinicSlug]);
  const { login } = usePatientAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [phone, setPhone] = useState("");
  const [fullName, setFullName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [consentPd, setConsentPd] = useState(false);
  const [consentMailing, setConsentMailing] = useState(false);
  const [policyOpened, { open: openPolicy, close: closePolicy }] = useDisclosure(false);

  const { data: agreement } = useAgreement();
  const sendCode = useSendCode();
  const verifyCode = useVerifyCode();

  const requireMailingConsent = agreement?.allow_registration_without_mailing_consent === false;
  const canSendCodeRegister = consentPd && (!requireMailingConsent || consentMailing);

  const normalizePhoneE164 = (): string => {
    let digits = phone.replace(/\D/g, "");
    if (digits.startsWith("8") && digits.length === 11) {
      digits = `7${digits.slice(1)}`;
    }
    if (digits.length === 10) {
      digits = `7${digits}`;
    }
    return `+${digits}`;
  };

  const digitsOnly = phone.replace(/\D/g, "");
  const canSendCodeLogin =
    digitsOnly.length === 10 ||
    (digitsOnly.length === 11 && (digitsOnly.startsWith("7") || digitsOnly.startsWith("8")));

  const handleSendCodeLogin = () => {
    const full = normalizePhoneE164();
    sendCode.mutate(full, {
      onSuccess: () => setStep("code"),
      onError: () => {},
    });
  };

  const handleSendCodeRegister = () => {
    const full = normalizePhoneE164();
    sendCode.mutate(full, {
      onSuccess: () => setStep("code"),
      onError: () => {},
    });
  };

  const handleVerify = () => {
    const full = normalizePhoneE164();
    const utm = getCurrentUtm();
    const fallback = clinicSlug ? `/c/${clinicSlug}/app` : ROUTE_PATHS.marketing.landing;
    const returnTo = safeAuthReturnTo(searchParams.get("returnTo"), fallback);
    verifyCode.mutate(
      {
        phone: full,
        code,
        consent_pd: true,
        consent_mailing: mode === "register" ? consentMailing : false,
        full_name: mode === "register" ? fullName.trim() || undefined : undefined,
        birth_date: mode === "register" ? birthDate.trim() || undefined : undefined,
        session_id: utm?.session_id,
        utm_source: utm?.utm_source ?? undefined,
        utm_medium: utm?.utm_medium ?? undefined,
        utm_campaign: utm?.utm_campaign ?? undefined,
        utm_content: utm?.utm_content ?? undefined,
        utm_term: utm?.utm_term ?? undefined,
        landing_page: utm?.landing_page ?? undefined,
        anchor: utm?.anchor ?? undefined,
      },
      {
        onSuccess: (data) => {
          login(data.access_token, data.patient_id);
          navigate(returnTo, { replace: true });
        },
        onError: () => {},
      }
    );
  };

  const apiError = sendCode.error || verifyCode.error;
  const message = apiError instanceof Error ? apiError.message : "";
  const isUnknownClinicSlug =
    apiError instanceof ApiErrorWithCode && apiError.code === "UNKNOWN_CLINIC_SLUG";
  const isClinicSlugRequired =
    apiError instanceof ApiErrorWithCode && apiError.code === "CLINIC_SLUG_REQUIRED";
  const isEmptyDb = message.includes(EMPTY_DB_MESSAGE) || message.includes("клиник");

  return (
    <Stack gap="sm">
      <div>
        <Title order={3}>
          {mode === "login" ? t("signIn.loginTitle") : t("signIn.registerTitle")}
        </Title>
        <Text size="sm" c="dimmed" mt={6}>
          {mode === "login" ? t("signIn.loginLead") : t("signIn.registerLead")}
        </Text>
      </div>
      <SegmentedControl
        fullWidth
        size="sm"
        color="slate"
        value={mode}
        onChange={(v) => {
          setMode(v as "login" | "register");
          setStep("phone");
          setCode("");
        }}
        data={[
          { label: t("signIn.modeLogin"), value: "login" },
          { label: t("signIn.modeRegister"), value: "register" },
        ]}
        aria-label={t("signIn.modeAria")}
      />
      {import.meta.env.DEV ? (
        <Alert color="gray" variant="light" title={t("signIn.devTitle")}>
          {t("signIn.devBody")}
        </Alert>
      ) : null}
      <Text size="xs" c="dimmed">
        {t("signIn.orSocial")}
      </Text>
      <Group gap="xs">
        <Button
          type="button"
          variant="outline"
          color="slate"
          size="xs"
            onClick={() => {
                window.location.href = `${API_BASE}/v1/auth/oauth/vk/start?${oauthStartQuery}`;
              }}
        >
          {t("signIn.vk")}
        </Button>
        <Button
          type="button"
          variant="outline"
          color="slate"
          size="xs"
            onClick={() => {
                window.location.href = `${API_BASE}/v1/auth/oauth/yandex/start?${oauthStartQuery}`;
              }}
        >
          {t("signIn.yandex")}
        </Button>
      </Group>
      {step === "phone" && (
        <>
          <TextInput
            label={t("signIn.phone")}
            placeholder={t("signIn.phonePlaceholder")}
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
          {mode === "register" && (
            <>
              <TextInput
                label={t("signIn.fullName")}
                placeholder={t("signIn.fullNamePlaceholder")}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
              <TextInput
                label={t("signIn.birthDate")}
                type="date"
                placeholder={t("signIn.birthPlaceholder")}
                value={birthDate}
                onChange={(e) => setBirthDate(e.target.value)}
              />
              <Checkbox
                label={
                  <>
                    {t("signIn.consentPd")}{" "}
                    <Anchor component="button" type="button" size="sm" onClick={openPolicy}>
                      {t("signIn.clinicPolicy")}
                    </Anchor>
                  </>
                }
                checked={consentPd}
                onChange={(e) => setConsentPd(e.currentTarget.checked)}
              />
              <Modal opened={policyOpened} onClose={closePolicy} title={t("signIn.policyTitle")} size="lg" centered>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  {agreement?.pd_agreement_text || t("signIn.policyMissing")}
                </Text>
              </Modal>
              <Checkbox
                label={t("signIn.consentMailing")}
                checked={consentMailing}
                onChange={(e) => setConsentMailing(e.currentTarget.checked)}
              />
            </>
          )}
          <Button
            type="button"
            color="slate"
            onClick={mode === "login" ? handleSendCodeLogin : handleSendCodeRegister}
            loading={sendCode.isPending}
            fullWidth
            disabled={mode === "login" ? !canSendCodeLogin : !canSendCodeRegister}
          >
            {t("signIn.getCode")}
          </Button>
        </>
      )}
      {step === "code" && (
        <>
          <Text size="sm" c="dimmed">
            {t("signIn.codeSent", { phone })}
          </Text>
          <TextInput
            label={t("signIn.smsCode")}
            placeholder="1234"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <Button
            type="button"
            color="slate"
            onClick={handleVerify}
            loading={verifyCode.isPending}
            fullWidth
          >
            {t("signIn.enter")}
          </Button>
          <Button
            type="button"
            variant="subtle"
            color={SEMANTIC.action.dismiss}
            onClick={() => setStep("phone")}
            fullWidth
          >
            {t("signIn.changeNumber")}
          </Button>
        </>
      )}
      {apiError && (
        <Alert
          color="red"
          variant="light"
          title={
            isClinicSlugRequired
              ? "Нужна ссылка клиники"
              : isUnknownClinicSlug
                ? "Клиника не найдена"
                : "Ошибка"
          }
        >
          {message}
          {isEmptyDb && " Добавьте клинику в настройках бэкенда."}
        </Alert>
      )}
    </Stack>
  );
}
