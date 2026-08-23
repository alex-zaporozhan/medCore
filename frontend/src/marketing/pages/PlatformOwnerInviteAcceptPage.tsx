import { API_BASE, newOutboundRequestId, parseFastApiErrorBody } from "@/api/client";
import { UiLocaleSwitch } from "@/i18n/UiLocaleSwitch";
import { ROUTE_PATHS } from "@/routePaths";
import { Alert, Box, Button, Container, Group, PasswordInput, Stack, Text, Title } from "@mantine/core";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

/**
 * Email landing after provision: token in query → POST /public/platform/owner-invite/accept.
 */
export default function PlatformOwnerInviteAcceptPage() {
  const { t } = useTranslation("marketing");
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token")?.trim() ?? "";
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const navigate = useNavigate();

  const messageForInviteFailure = (status: number, raw: string): string => {
    const parsed = parseFastApiErrorBody(raw || "{}");
    const code = (parsed.code ?? "").trim();
    if (code === "password_too_short") return t("invite.passwordTooShort");
    if (code === "invalid_or_expired_token") return t("invite.invalidOrExpired");
    if (code === "invite_accept_failed") return t("invite.failed");
    if (code === "rate_limited" || status === 429) return t("invite.rateLimited");
    return parsed.rawMessage?.trim() || t("invite.failed");
  };

  const submit = async () => {
    setErr(null);
    if (password.length < 8) {
      setErr(t("invite.passwordTooShort"));
      return;
    }
    if (!token) {
      setErr(t("invite.noToken"));
      return;
    }
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/v1/public/platform/owner-invite/accept`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Request-Id": newOutboundRequestId(),
        },
        body: JSON.stringify({ token, password }),
      });
      const text = await r.text().catch(() => "");
      if (!r.ok) {
        setErr(messageForInviteFailure(r.status, text));
        return;
      }
      navigate(ROUTE_PATHS.admin.login);
    } catch (error: unknown) {
      console.error("owner invite accept failed", error);
      setErr(t("invite.network"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box className="marketing-gradient-bg" style={{ minHeight: "100vh", padding: "40px 16px" }}>
      <Container size="sm">
        <Stack gap="md">
          <Group justify="space-between" wrap="wrap" gap="sm" align="flex-start">
            <Title order={2}>{t("invite.title")}</Title>
            <UiLocaleSwitch />
          </Group>
          {!token ? (
            <Alert color="red">{t("invite.missingToken")}</Alert>
          ) : (
            <>
              <Text size="sm" c="dimmed">
                {t("invite.lead")}
              </Text>
              <PasswordInput
                label={t("invite.password")}
                value={password}
                onChange={(e) => setPassword(e.currentTarget.value)}
                autoComplete="new-password"
                disabled={busy}
              />
              {err ? (
                <Alert color="red" title={t("invite.errorTitle")}>
                  {err}
                </Alert>
              ) : null}
              <Button onClick={() => void submit()} loading={busy} disabled={busy}>
                {t("invite.submit")}
              </Button>
            </>
          )}
          <Text size="sm">
            <Link to={ROUTE_PATHS.marketing.landing}>← {t("signup.backHome")}</Link>
          </Text>
        </Stack>
      </Container>
    </Box>
  );
}
