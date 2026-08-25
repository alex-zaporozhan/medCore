import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiErrorWithCode, setAdminClinicId, setAdminId, setAdminToken } from "@/api/client";
import { queryKeys } from "@/queryKeys";
import { commonErrorI18nKey, localizedApiErrorText } from "@/shared/errors";
import { Alert, Button, Stack, Text, TextInput, Title } from "@mantine/core";
import { ROUTE_PATHS } from "@/routePaths";
import { defaultReturnToForTab, safeAuthReturnTo } from "@/auth/signInReturnTo";

const MIN_PASSWORD_LENGTH = 8;

type FormError =
  | { kind: "passwordMin" }
  | { kind: "api"; code?: string; text: string };

export function ClinicStaffSignInPanel() {
  const { t } = useTranslation("auth");
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<FormError | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError({ kind: "passwordMin" });
      return;
    }
    setError(null);
    setLoading(true);
    const fallback = defaultReturnToForTab("clinic");
    const returnTo = safeAuthReturnTo(searchParams.get("returnTo"), fallback);
    try {
      const res = await api.post<{
        access_token: string;
        admin_id: string;
        clinic_id: string;
        full_name: string | null;
      }>("/v1/admin/auth/login", { email: email.trim().toLowerCase(), password });
      setAdminToken(res.access_token);
      if (res.admin_id) setAdminId(res.admin_id);
      if (res.clinic_id) setAdminClinicId(res.clinic_id);
      await queryClient.invalidateQueries({ queryKey: queryKeys.adminSession() });
      navigate(returnTo, { replace: true });
    } catch (err) {
      setError({
        kind: "api",
        code: err instanceof ApiErrorWithCode ? err.code : undefined,
        text: localizedApiErrorText(err, t as never, "clinic.signInFailed"),
      });
    } finally {
      setLoading(false);
    }
  };

  const mappedKey = error?.kind === "api" ? commonErrorI18nKey(error.code) : null;
  const errorText =
    error?.kind === "passwordMin"
      ? t("clinic.passwordMinError", { count: MIN_PASSWORD_LENGTH })
      : mappedKey
        ? t(mappedKey as never, { ns: "common" })
        : error?.kind === "api"
          ? error.text
          : undefined;

  return (
    <Stack gap="md">
      <div>
        <Title order={3}>{t("clinic.panelTitle")}</Title>
        <Text size="sm" c="dimmed" mt={6}>
          {t("clinic.panelSubtitle")}
        </Text>
      </div>
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          {errorText && (
            <Alert color="red" title={t("clinic.errorTitle")} onClose={() => setError(null)} withCloseButton>
              {errorText}
            </Alert>
          )}
          <TextInput
            label={t("clinic.email")}
            type="email"
            placeholder="admin@example.com"
            value={email}
            onChange={(e) => setEmail(e.currentTarget.value)}
            required
            autoComplete="username"
          />
          <TextInput
            label={t("clinic.password")}
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.currentTarget.value)}
            required
            minLength={MIN_PASSWORD_LENGTH}
            description={t("clinic.passwordMinHint", { count: MIN_PASSWORD_LENGTH })}
            autoComplete="current-password"
          />
          <Button type="submit" loading={loading} fullWidth color="slate" radius="md">
            {t("signIn")}
          </Button>
        </Stack>
      </form>
      <Text size="sm" c="dimmed">
        <Link to={ROUTE_PATHS.marketing.landing}>{t("clinic.home")}</Link>
      </Text>
    </Stack>
  );
}
