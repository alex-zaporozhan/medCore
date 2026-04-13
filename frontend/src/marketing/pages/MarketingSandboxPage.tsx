import { API_BASE, newOutboundRequestId } from "@/api/client";
import { TurnstileWidget } from "@/marketing/components/TurnstileWidget";
import { parseEnterpriseLeadSubmitFailure } from "@/marketing/enterpriseLeadPublic";
import { ROUTE_PATHS } from "@/routePaths";
import { Anchor, Box, Button, Paper, Stack, Text, TextInput, Title } from "@mantine/core";
import { useState } from "react";
import { Link } from "react-router-dom";

/**
 * Публичная заглушка демо-контура: контакт уходит в ту же очередь заявок, что и корпоративная форма.
 */
export default function MarketingSandboxPage() {
  const [contact, setContact] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [turnstileSiteKey, setTurnstileSiteKey] = useState<string | null>(null);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);

  const submit = (tokenOverride: string | null) => {
    const v = contact.trim();
    if (!v || busy) return;
    const t = tokenOverride?.trim();
    if (turnstileSiteKey && !t) {
      setError("Сначала пройдите проверку Turnstile, затем снова нажмите кнопку.");
      return;
    }
    setError(null);
    setBusy(true);
    void (async () => {
      try {
        const body: Record<string, unknown> = {
          name: "Ранний доступ к демо",
          company_name: "Публичная страница",
          phone_or_email: v,
          lead_source: "sandbox_demo",
        };
        if (t) body.turnstile_token = t;
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
        setError("Не удалось отправить заявку. Проверьте соединение и повторите попытку.");
      } finally {
        setBusy(false);
      }
    })();
  };

  return (
    <Box
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg-main)",
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
              Демо-версия системы готовится к запуску
            </Title>
            <Text size="sm" c="dimmed" mt="md" style={{ lineHeight: 1.65 }}>
              Мы обновляем публичную песочницу, чтобы показать вам всю мощь наших новых ИИ-модулей и финансового
              учёта. Оставьте контакты, и мы пришлём вам персональный доступ первыми.
            </Text>
          </div>
          {sent ? (
            <Text size="sm" fw={500}>
              Заявка принята, мы свяжемся с вами.
            </Text>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const tok = turnstileSiteKey ? turnstileToken : null;
                submit(tok);
              }}
            >
              <Stack gap="sm">
                <TextInput
                  label="Email или Telegram"
                  placeholder="you@company.ru или @username"
                  value={contact}
                  onChange={(e) => setContact(e.currentTarget.value)}
                  type="text"
                  autoComplete="email"
                />
                {turnstileSiteKey ? (
                  <Stack gap="xs">
                    <Text size="sm" fw={500}>
                      Проверка антиспама
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
                  Получить ранний доступ
                </Button>
              </Stack>
            </form>
          )}
          <Anchor component={Link} to={ROUTE_PATHS.marketing.landing} size="sm" c="dimmed">
            ← Вернуться на главную
          </Anchor>
        </Stack>
      </Paper>
    </Box>
  );
}
