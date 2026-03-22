import { usePatientAuth } from "@/contexts/PatientAuthContext";
import { useAgreement, useSendCode, useVerifyCode } from "@/hooks/useAuth";
import {
  Alert,
  Anchor,
  Button,
  Center,
  Checkbox,
  Group,
  Modal,
  Paper,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { getCurrentUtm } from "@/shared/utmTracking";
import { SEMANTIC } from "@/shared/semanticUi";
import { ROUTE_PATHS } from "@/routePaths";

const oauthRedirectHome = encodeURIComponent(ROUTE_PATHS.patient.home);

const EMPTY_DB_MESSAGE = "В базе данных нет ни одной клиники";

export default function LoginPage() {
  const navigate = useNavigate();
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
  /** Должно совпадать с `AuthService._normalize_phone` на бэкенде. */
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
          navigate(ROUTE_PATHS.patient.home, { replace: true });
        },
        onError: () => {},
      }
    );
  };

  const apiError = sendCode.error || verifyCode.error;
  const message = apiError instanceof Error ? apiError.message : "";
  const isEmptyDb = message.includes(EMPTY_DB_MESSAGE) || message.includes("клиник");

  return (
    <Center h="100%">
      <Paper
        radius="lg"
        shadow="md"
        p="xl"
        maw={420}
        w="100%"
        withBorder
      >
        <Stack gap="sm">
          <Title order={2}>{mode === "login" ? "Вход в личный кабинет" : "Регистрация в клинике"}</Title>
          <Text size="sm" c="dimmed">
            {mode === "login"
              ? "Если вы уже записывались в клинику, просто введите номер телефона — мы отправим SMS‑код для входа."
              : "Если вы впервые записываетесь в клинику, заполните данные и получите SMS‑код для входа."}
          </Text>
          <SegmentedControl
            fullWidth
            size="sm"
            value={mode}
            onChange={(v) => {
              setMode(v as "login" | "register");
              setStep("phone");
              setCode("");
            }}
            data={[
              { label: "Уже есть запись", value: "login" },
              { label: "Я новый пациент", value: "register" },
            ]}
            aria-label="Режим: вход или регистрация"
          />
          <Text size="xs" c="dimmed">
            Или войдите через социальную сеть:
          </Text>
          <Group gap="xs">
            <Button
              type="button"
              variant="outline"
              color={SEMANTIC.action.send}
              size="xs"
              onClick={() => {
                window.location.href = `/api/v1/auth/oauth/vk/start?redirect=${oauthRedirectHome}`;
              }}
            >
              Войти через VK
            </Button>
            <Button
              type="button"
              variant="outline"
              color={SEMANTIC.action.send}
              size="xs"
              onClick={() => {
                window.location.href = `/api/v1/auth/oauth/yandex/start?redirect=${oauthRedirectHome}`;
              }}
            >
              Войти через Яндекс
            </Button>
          </Group>
          {step === "phone" && (
            <>
              <TextInput
                label="Телефон"
                placeholder="+7 900 123 45 67"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
              {mode === "register" && (
                <>
                  <TextInput
                    label="ФИО"
                    placeholder="Иванов Иван Иванович"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                  <TextInput
                    label="Дата рождения"
                    type="date"
                    placeholder="ГГГГ-ММ-ДД"
                    value={birthDate}
                    onChange={(e) => setBirthDate(e.target.value)}
                  />
                  <Checkbox
                    label={
                      <>
                        Я согласен(а) на обработку персональных данных в соответствии с{" "}
                        <Anchor component="button" type="button" size="sm" onClick={openPolicy}>
                          политикой клиники
                        </Anchor>
                      </>
                    }
                    checked={consentPd}
                    onChange={(e) => setConsentPd(e.currentTarget.checked)}
                  />
                  <Modal opened={policyOpened} onClose={closePolicy} title="Политика обработки ПД" size="lg">
                    <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                      {agreement?.pd_agreement_text || "Текст политики не задан. Обратитесь в клинику."}
                    </Text>
                  </Modal>
                  <Checkbox
                    label="Я согласен(а) получать рассылку и новости от клиники (акции, напоминания)"
                    checked={consentMailing}
                    onChange={(e) => setConsentMailing(e.currentTarget.checked)}
                  />
                </>
              )}
              <Button
                type="button"
                color={SEMANTIC.action.confirm}
                onClick={mode === "login" ? handleSendCodeLogin : handleSendCodeRegister}
                loading={sendCode.isPending}
                fullWidth
                disabled={mode === "login" ? !canSendCodeLogin : !canSendCodeRegister}
              >
                Получить код
              </Button>
            </>
          )}
          {step === "code" && (
            <>
              <Text size="sm" c="dimmed">
                Код отправлен на {phone}. Введите его, чтобы продолжить.
              </Text>
              <TextInput
                label="Код из SMS"
                placeholder="1234"
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
              <Button
                type="button"
                color={SEMANTIC.action.confirm}
                onClick={handleVerify}
                loading={verifyCode.isPending}
                fullWidth
              >
                Войти
              </Button>
              <Button
                type="button"
                variant="subtle"
                color={SEMANTIC.action.dismiss}
                onClick={() => setStep("phone")}
                fullWidth
              >
                Изменить номер
              </Button>
            </>
          )}
          {apiError && (
            <Alert color="red" variant="light" title="Ошибка">
              {message}
              {isEmptyDb && " Добавьте клинику в настройках бэкенда."}
            </Alert>
          )}
        </Stack>
      </Paper>
    </Center>
  );
}
