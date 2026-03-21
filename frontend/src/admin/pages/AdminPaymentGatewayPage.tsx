import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useClinics, useSetClinicPaymentGatewayCredentials, useUpdateClinicMutation } from "@/hooks";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { Button, Paper, Select, Stack, Text, TextInput } from "@mantine/core";
import { ContextBar, QueryErrorAlert } from "@/shared/ui";
import { useState, useEffect } from "react";

const GATEWAY_OPTIONS = [
  { value: "yookassa", label: "ЮKassa" },
  { value: "tinkoff", label: "Тинькофф" },
  { value: "sber", label: "Сбербанк" },
  { value: "robokassa", label: "Robokassa" },
  { value: "stripe", label: "Stripe" },
  { value: "paypal", label: "PayPal" },
  { value: "custom", label: "Своя касса" },
];

export default function AdminPaymentGatewayPage() {
  const { currentClinicId } = useAdminClinic();
  const { data: clinicsData } = useClinics();
  const updateClinic = useUpdateClinicMutation();
  const clinic = currentClinicId
    ? (clinicsData ?? []).find((c) => c.id === currentClinicId)
    : null;
  const [gateway, setGateway] = useState(clinic?.payment_gateway ?? "yookassa");
  const [customName, setCustomName] = useState(clinic?.payment_gateway_custom_name ?? "");
  const [yookassaShopId, setYookassaShopId] = useState(clinic?.yookassa_shop_id ?? "");
  const [yookassaSecretKey, setYookassaSecretKey] = useState("");
  const [tinkoffTerminalKey, setTinkoffTerminalKey] = useState("");
  const [tinkoffPassword, setTinkoffPassword] = useState("");
  const [sberLogin, setSberLogin] = useState("");
  const [sberPassword, setSberPassword] = useState("");
  const [robokassaMerchantLogin, setRobokassaMerchantLogin] = useState("");
  const [robokassaPassword1, setRobokassaPassword1] = useState("");
  const [robokassaPassword2, setRobokassaPassword2] = useState("");
  const [stripeSecretKey, setStripeSecretKey] = useState("");
  const [stripePublishableKey, setStripePublishableKey] = useState("");
  const [paypalClientId, setPaypalClientId] = useState("");
  const [paypalClientSecret, setPaypalClientSecret] = useState("");
  const [customIdentifier, setCustomIdentifier] = useState("");
  const [customKey, setCustomKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [credentialsError, setCredentialsError] = useState<string | null>(null);
  const [clinicUpdateError, setClinicUpdateError] = useState<unknown>(null);
  const setCredentialsMutation = useSetClinicPaymentGatewayCredentials(currentClinicId ?? null);

  useEffect(() => {
    if (clinic) {
      setGateway(clinic.payment_gateway ?? "yookassa");
      setCustomName(clinic.payment_gateway_custom_name ?? "");
      setYookassaShopId(clinic.yookassa_shop_id ?? "");
    }
  }, [clinic?.id, clinic?.payment_gateway, clinic?.payment_gateway_custom_name, clinic?.yookassa_shop_id]);

  const handleSave = async () => {
    if (!currentClinicId) return;
    setSaving(true);
    setCredentialsError(null);
    setClinicUpdateError(null);
    try {
      const body: Record<string, unknown> = {
        payment_gateway: gateway,
        payment_gateway_custom_name: gateway === "custom" ? (customName.trim() || null) : null,
      };
      if (gateway === "yookassa") {
        body.yookassa_shop_id = yookassaShopId.trim() || null;
        if (yookassaSecretKey.trim()) body.yookassa_secret_key = yookassaSecretKey.trim();
      }
      try {
        await updateClinic.mutateAsync({ clinicId: currentClinicId, body });
      } catch (e) {
        setClinicUpdateError(e);
        return;
      }
      setYookassaSecretKey("");

      if (gateway !== "yookassa") {
        let credentialsObject: Record<string, string> | null = null;
        if (gateway === "tinkoff") {
          credentialsObject = {
            terminal_key: tinkoffTerminalKey.trim(),
            password: tinkoffPassword.trim(),
          };
        } else if (gateway === "sber") {
          credentialsObject = {
            userName: sberLogin.trim(),
            password: sberPassword.trim(),
          };
        } else if (gateway === "robokassa") {
          credentialsObject = {
            merchant_login: robokassaMerchantLogin.trim(),
            password1: robokassaPassword1.trim(),
            password2: robokassaPassword2.trim(),
          };
        } else if (gateway === "stripe") {
          credentialsObject = {
            secret_key: stripeSecretKey.trim(),
            publishable_key: stripePublishableKey.trim(),
          };
        } else if (gateway === "paypal") {
          credentialsObject = {
            client_id: paypalClientId.trim(),
            client_secret: paypalClientSecret.trim(),
          };
        } else if (gateway === "custom") {
          credentialsObject = {
            identifier: customIdentifier.trim(),
            key: customKey.trim(),
          };
        }

        if (credentialsObject) {
          const hasAnyValue = Object.values(credentialsObject).some((v) => !!v);
          if (hasAnyValue) {
            try {
              await setCredentialsMutation.mutateAsync({
                gateway,
                payload: JSON.stringify(credentialsObject),
              });
            } catch (e) {
              const message =
                e instanceof Error ? e.message : "Не удалось сохранить ключи кассы. Попробуйте ещё раз.";
              setCredentialsError(message);
            }
          }
        }
      }
    } finally {
      setSaving(false);
    }
  };

  if (!currentClinicId) {
    return (
      <Stack>
        <ContextBar title="Касса" />
        <EmptyStateHint title="Выберите клинику" />
      </Stack>
    );
  }

  return (
    <Stack>
      <ContextBar title="Платёжный шлюз" />
      <Text size="sm" c="dimmed">
        Выберите одну платёжную систему. Укажите данные из личного кабинета выбранного провайдера. Активна одна касса на клинику.
      </Text>
      {clinicUpdateError != null ? (
        <QueryErrorAlert error={clinicUpdateError} title="Не удалось сохранить настройки клиники" />
      ) : null}
      {credentialsError && (
        <QueryErrorAlert error={credentialsError} title="Не удалось сохранить ключи кассы" />
      )}
      <Paper p="md" withBorder>
        <Stack gap="md">
          <Select
            label="Платёжная система"
            data={GATEWAY_OPTIONS}
            value={gateway}
            onChange={(v) => setGateway(v ?? "yookassa")}
          />

          {gateway === "yookassa" && (
            <>
              <TextInput
                label="Идентификатор магазина (Shop ID)"
                placeholder="123456"
                value={yookassaShopId}
                onChange={(e) => setYookassaShopId(e.currentTarget.value)}
                description="Идентификатор магазина из личного кабинета ЮKassa (Настройки → Идентификатор магазина). Используется для создания платежей и возвратов."
              />
              <TextInput
                type="password"
                label="Секретный ключ"
                placeholder="Оставьте пустым, чтобы не менять сохранённый ключ"
                value={yookassaSecretKey}
                onChange={(e) => setYookassaSecretKey(e.currentTarget.value)}
                description="Секретный ключ из личного кабинета ЮKassa. Хранится в зашифрованном виде. Введите новый ключ только при смене."
              />
            </>
          )}

          {gateway === "tinkoff" && (
            <>
              <TextInput
                label="Идентификатор терминала (Terminal Key)"
                placeholder=""
                value={tinkoffTerminalKey}
                onChange={(e) => setTinkoffTerminalKey(e.currentTarget.value)}
                description="Идентификатор терминала из личного кабинета Тинькофф Касса. Выдаётся при подключении."
              />
              <TextInput
                type="password"
                label="Пароль терминала"
                placeholder=""
                value={tinkoffPassword}
                onChange={(e) => setTinkoffPassword(e.currentTarget.value)}
                description="Пароль от терминала из личного кабинета Тинькофф Касса. Используется для подписи запросов. Хранится в зашифрованном виде."
              />
            </>
          )}

          {gateway === "sber" && (
            <>
              <TextInput
                label="Логин (UserName)"
                placeholder=""
                value={sberLogin}
                onChange={(e) => setSberLogin(e.currentTarget.value)}
                description="Логин для доступа к API Сбербанка (эквайринг / SberPay). Уточните в договоре и личном кабинете банка."
              />
              <TextInput
                type="password"
                label="Пароль API"
                placeholder=""
                value={sberPassword}
                onChange={(e) => setSberPassword(e.currentTarget.value)}
                description="Пароль для API Сбербанка. Хранится в зашифрованном виде."
              />
            </>
          )}

          {gateway === "robokassa" && (
            <>
              <TextInput
                label="Идентификатор магазина (Merchant Login)"
                placeholder=""
                value={robokassaMerchantLogin}
                onChange={(e) => setRobokassaMerchantLogin(e.currentTarget.value)}
                description="Логин магазина из личного кабинета Robokassa."
              />
              <TextInput
                type="password"
                label="Пароль #1"
                placeholder=""
                value={robokassaPassword1}
                onChange={(e) => setRobokassaPassword1(e.currentTarget.value)}
                description="Первый пароль (Result URL, Success). Используется при приёме платежей. Хранится в зашифрованном виде."
              />
              <TextInput
                type="password"
                label="Пароль #2"
                placeholder=""
                value={robokassaPassword2}
                onChange={(e) => setRobokassaPassword2(e.currentTarget.value)}
                description="Второй пароль (Result URL, Fail / уведомления). Для проверки подписи уведомлений от Robokassa."
              />
            </>
          )}

          {gateway === "stripe" && (
            <>
              <TextInput
                type="password"
                label="Secret key"
                placeholder="sk_live_... или sk_test_..."
                value={stripeSecretKey}
                onChange={(e) => setStripeSecretKey(e.currentTarget.value)}
                description="Секретный ключ из Stripe Dashboard (Developers → API keys). Для приёма платежей используется Secret key. Тестовый ключ — для sandbox. Хранится в зашифрованном виде."
              />
              <TextInput
                label="Publishable key (опционально)"
                placeholder="pk_live_..."
                value={stripePublishableKey}
                onChange={(e) => setStripePublishableKey(e.currentTarget.value)}
                description="Публичный ключ для клиентских форм (например, Stripe Elements). Не обязателен для серверного создания платежей."
              />
            </>
          )}

          {gateway === "paypal" && (
            <>
              <TextInput
                label="Client ID"
                placeholder=""
                value={paypalClientId}
                onChange={(e) => setPaypalClientId(e.currentTarget.value)}
                description="Client ID приложения из PayPal Developer Dashboard (My Apps & Credentials). Для production — Live, для тестов — Sandbox."
              />
              <TextInput
                type="password"
                label="Client Secret"
                placeholder=""
                value={paypalClientSecret}
                onChange={(e) => setPaypalClientSecret(e.currentTarget.value)}
                description="Client Secret приложения. Хранится в зашифрованном виде."
              />
            </>
          )}

          {gateway === "custom" && (
            <>
              <TextInput
                label="Название своей кассы"
                placeholder="PayPal, Stripe, другая интеграция"
                value={customName}
                onChange={(e) => setCustomName(e.currentTarget.value)}
                description="Только отображаемое название. Ключи и оплата настраиваются вне системы."
              />
              <TextInput
                label="Идентификатор"
                placeholder=""
                value={customIdentifier}
                onChange={(e) => setCustomIdentifier(e.currentTarget.value)}
                description="Идентификатор или логин для своей кассы (опционально)."
              />
              <TextInput
                type="password"
                label="Ключ"
                placeholder=""
                value={customKey}
                onChange={(e) => setCustomKey(e.currentTarget.value)}
                description="Секретный ключ или пароль для своей кассы (опционально)."
              />
            </>
          )}

          <Button onClick={handleSave} loading={saving}>
            Сохранить
          </Button>
        </Stack>
      </Paper>
    </Stack>
  );
}
