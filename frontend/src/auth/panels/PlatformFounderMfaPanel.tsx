import { API_BASE, parseFastApiErrorBody } from "@/api/client";
import {
  clearPendingPlatformFounderMfaToken,
  getPendingPlatformFounderMfaToken,
} from "@/auth/platformFounderMfaSession";
import { clearFounderToken, setFounderToken } from "@/marketing/platformFounderSession";
import { ROUTE_PATHS } from "@/routePaths";
import { Alert, Anchor, Button, Group, Stack, Text, TextInput } from "@mantine/core";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { defaultReturnToForTab, safeAuthReturnTo } from "@/auth/signInReturnTo";

export function PlatformFounderMfaPanel() {
  const { t } = useTranslation("founder");
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mfaToken] = useState<string | null>(() => getPendingPlatformFounderMfaToken());
  const [totpCode, setTotpCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const fallbackReturn = defaultReturnToForTab("founder");

  const messageFromBodyText = (text: string, status: number): string => {
    const p = parseFastApiErrorBody(text || "{}");
    return p.rawMessage?.trim() || t("errors.status", { status });
  };

  const goAfterSuccess = () => {
    clearPendingPlatformFounderMfaToken();
    const returnTo = safeAuthReturnTo(searchParams.get("returnTo"), fallbackReturn);
    navigate(returnTo, { replace: true });
  };

  const goBackToLogin = () => {
    clearPendingPlatformFounderMfaToken();
    clearFounderToken();
    navigate({ pathname: ROUTE_PATHS.platform.login, search: searchParams.toString() ? `?${searchParams.toString()}` : "" }, { replace: true });
  };

  const submitMfa = async () => {
    const token = mfaToken ?? getPendingPlatformFounderMfaToken();
    if (!token) {
      setError("Сессия MFA устарела. Войдите снова.");
      goBackToLogin();
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/v1/platform/auth/login/mfa`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mfa_token: token,
          totp_code: totpCode.trim(),
        }),
      });
      const text = await r.text().catch(() => "");
      let data: Record<string, unknown> = {};
      try {
        if (text) data = JSON.parse(text) as Record<string, unknown>;
      } catch {
        data = {};
      }
      if (!r.ok) {
        setError(messageFromBodyText(text, r.status));
        return;
      }
      const access = typeof data.access_token === "string" ? data.access_token : "";
      if (access) {
        setFounderToken(access);
        goAfterSuccess();
        return;
      }
      setError(t("mfa.unexpected"));
    } finally {
      setBusy(false);
    }
  };

  if (!mfaToken) {
    return (
      <Stack gap="md">
        <Text size="sm">{t("mfa.missing")}</Text>
        <Button variant="default" onClick={goBackToLogin}>
          {t("mfa.backToLogin")}
        </Button>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <Text size="sm">
        {t("mfa.hint")}
      </Text>
      <TextInput
        label={t("mfa.code")}
        placeholder="000000"
        value={totpCode}
        onChange={(e) => setTotpCode(e.currentTarget.value)}
        autoComplete="one-time-code"
        autoFocus
      />
      <Group justify="space-between" wrap="nowrap" gap="sm">
        <Button variant="default" onClick={goBackToLogin}>
          {t("mfa.back")}
        </Button>
        <Button loading={busy} color="slate" radius="md" onClick={() => void submitMfa()}>
          {t("mfa.confirm")}
        </Button>
      </Group>

      {error ? (
        <Alert color="red" variant="light" title={t("mfa.errorTitle")}>
          {error}
        </Alert>
      ) : null}

      <Anchor component={Link} to={ROUTE_PATHS.marketing.landing} size="sm">
        {t("mfa.home")}
      </Anchor>
    </Stack>
  );
}
