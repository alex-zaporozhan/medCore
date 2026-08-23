import { API_BASE, newOutboundRequestId } from "@/api/client";
import { MarketingPublicChrome } from "@/marketing/components/MarketingPublicChrome";
import { TurnstileWidget } from "@/marketing/components/TurnstileWidget";
import { parseEnterpriseLeadSubmitFailure } from "@/marketing/enterpriseLeadPublic";
import { ROUTE_PATHS } from "@/routePaths";
import { Anchor, Box, Button, Paper, Stack, Text, TextInput, Title } from "@mantine/core";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

/** Public demo-contour stub: contact goes to the same lead queue as the corporate form. */
export default function MarketingSandboxPage() {
  const { t } = useTranslation("marketing");
  const [contact, setContact] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [turnstileSiteKey, setTurnstileSiteKey] = useState<string | null>(null);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);

  const submit = (tokenOverride: string | null) => {
    const v = contact.trim();
    if (!v || busy) return;
    const tok = tokenOverride?.trim();
    if (turnstileSiteKey && !tok) {
      setError(t("sandbox.needCaptcha"));
      return;
    }
    setError(null);
    setBusy(true);
    void (async () => {
      try {
        const body: Record<string, unknown> = {
          name: "Early demo access",
          company_name: "Public page",
          phone_or_email: v,
          lead_source: "sandbox_demo",
        };
        if (tok) body.turnstile_token = tok;
        const r = await fetch(`${API_BASE}/v1/platform-leads/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Request-Id": newOutboundRequestId(),
          },
          body: JSON.stringify(body),
        });
        const text = await r.text().catch(() => "");
        if (!r.ok) {
          const parsed = parseEnterpriseLeadSubmitFailure(r.status, text || "{}");
          if (parsed.code === "captcha_required" && parsed.siteKey) {
            setTurnstileSiteKey(parsed.siteKey);
            setTurnstileToken(null);
            setError(parsed.message);
            return;
          }
          setTurnstileSiteKey(null);
          setTurnstileToken(null);
          setError(parsed.message);
          return;
        }
        setTurnstileSiteKey(null);
        setTurnstileToken(null);
        setSent(true);
      } catch {
        setError(t("sandbox.network"));
      } finally {
        setBusy(false);
      }
    })();
  };

  return (
    <Box
      style={{
        minHeight: "100vh",
        background: "var(--bg-main)",
      }}
    >
      <MarketingPublicChrome>
        <Box
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px 16px",
          }}
        >
      <Paper
        p="xl"
        radius="md"
        shadow="lg"
        maw={520}
        w="100%"
        style={{ background: "var(--bg-card)", border: "1px solid var(--divider)" }}
      >
        <Stack gap="lg">
          <div>
            <Title order={1} size="h2" style={{ color: "var(--text-main)" }}>
              {t("sandbox.title")}
            </Title>
            <Text size="sm" c="dimmed" mt="md" style={{ lineHeight: 1.65 }}>
              {t("sandbox.lead")}
            </Text>
          </div>
          {sent ? (
            <Text size="sm" fw={500}>
              {t("sandbox.success")}
            </Text>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const cap = turnstileSiteKey ? turnstileToken : null;
                submit(cap);
              }}
            >
              <Stack gap="sm">
                <TextInput
                  label={t("sandbox.contact")}
                  placeholder={t("sandbox.contactPlaceholder")}
                  value={contact}
                  onChange={(e) => setContact(e.currentTarget.value)}
                  type="text"
                  autoComplete="email"
                />
                {turnstileSiteKey ? (
                  <Stack gap="xs">
                    <Text size="sm" fw={500}>
                      {t("sandbox.captcha")}
                    </Text>
                    <TurnstileWidget
                      siteKey={turnstileSiteKey}
                      onToken={(tok) => setTurnstileToken(tok)}
                      onExpire={() => setTurnstileToken(null)}
                    />
                  </Stack>
                ) : null}
                {error ? (
                  <Text size="sm" c="red">
                    {error}
                  </Text>
                ) : null}
                <Button type="submit" loading={busy} disabled={!contact.trim()}>
                  {t("sandbox.submit")}
                </Button>
              </Stack>
            </form>
          )}
          <Anchor component={Link} to={ROUTE_PATHS.marketing.landing} size="sm" c="dimmed">
            {t("sandbox.backHome")}
          </Anchor>
        </Stack>
      </Paper>
        </Box>
      </MarketingPublicChrome>
    </Box>
  );
}
