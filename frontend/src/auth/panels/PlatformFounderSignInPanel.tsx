import { API_BASE, parseFastApiErrorBody } from "@/api/client";
import { setPendingPlatformFounderMfaToken } from "@/auth/platformFounderMfaSession";
import { setFounderToken } from "@/marketing/platformFounderSession";
import { ROUTE_PATHS } from "@/routePaths";
import { Alert, Anchor, Button, PasswordInput, Stack, Text, TextInput } from "@mantine/core";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { defaultReturnToForTab, safeAuthReturnTo } from "@/auth/signInReturnTo";

export function PlatformFounderSignInPanel() {
  const { t } = useTranslation("auth");
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const fallbackReturn = defaultReturnToForTab("founder");

  const messageFromBodyText = (text: string, status: number): string => {
    const p = parseFastApiErrorBody(text || "{}");
    return p.rawMessage?.trim() || t("founder.errorStatus", { status });
  };

  const goAfterSuccess = () => {
    const returnTo = safeAuthReturnTo(searchParams.get("returnTo"), fallbackReturn);
    navigate(returnTo, { replace: true });
  };

  const submitCredentials = async () => {
    setError(null);
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/v1/platform/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });
      const text = await r.text().catch(() => "");
      let data: Record<string, unknown> = {};
      try {
        if (text) data = JSON.parse(text) as Record<string, unknown>;
      } catch {
        data = {};
      }
      if (r.status === 503 || !r.ok) {
        setError(messageFromBodyText(text, r.status));
        return;
      }
      if (data.mfa_required === true && typeof data.mfa_token === "string") {
        setPendingPlatformFounderMfaToken(data.mfa_token);
        const qs = searchParams.toString();
        navigate(
          { pathname: ROUTE_PATHS.platform.loginMfa, search: qs ? `?${qs}` : "" },
          { replace: true },
        );
        return;
      }
      const access = typeof data.access_token === "string" ? data.access_token : "";
      if (access) {
        setFounderToken(access);
        goAfterSuccess();
        return;
      }
      setError(t("founder.unexpectedResponse"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("founder.signInFailed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack gap="md">
      <TextInput
        label={t("founder.email")}
        type="email"
        autoComplete="username"
        value={email}
        onChange={(e) => setEmail(e.currentTarget.value)}
      />
      <PasswordInput
        label={t("founder.password")}
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.currentTarget.value)}
      />
      <Text size="xs" c="dimmed">
        {t("founder.mfaHint")}
      </Text>
      <Button loading={busy} onClick={() => void submitCredentials()} fullWidth color="slate" radius="md">
        {t("founder.signIn")}
      </Button>

      {error ? (
        <Alert color="red" variant="light" title={t("founder.errorTitle")}>
          {error}
        </Alert>
      ) : null}

      <Anchor component={Link} to={ROUTE_PATHS.marketing.landing} size="sm">
        {t("founder.home")}
      </Anchor>
    </Stack>
  );
}
