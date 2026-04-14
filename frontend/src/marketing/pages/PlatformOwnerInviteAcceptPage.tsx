import { API_BASE, newOutboundRequestId } from "@/api/client";
import { ROUTE_PATHS } from "@/routePaths";
import { Alert, Box, Button, Container, PasswordInput, Stack, Text, Title } from "@mantine/core";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

/**
 * Страница из письма (LEAD A1): token в query → POST /public/platform/owner-invite/accept.
 */
export default function PlatformOwnerInviteAcceptPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token")?.trim() ?? "";
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const navigate = useNavigate();

  const submit = async () => {
    setErr(null);
    if (password.length < 8) {
      setErr("Пароль не короче 8 символов.");
      return;
    }
    if (!token) {
      setErr("Нет токена в ссылке.");
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
      const data = (await r.json().catch(() => ({}))) as Record<string, unknown>;
      if (!r.ok) {
        const detail = data.detail as Record<string, unknown> | string | undefined;
        const msg =
          typeof detail === "object" && detail && typeof detail.message === "string"
            ? detail.message
            : "Не удалось установить пароль.";
        setErr(msg);
        return;
      }
      navigate(ROUTE_PATHS.admin.login);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box className="marketing-gradient-bg" style={{ minHeight: "100vh", padding: "40px 16px" }}>
      <Container size="sm">
        <Stack gap="md">
          <Title order={2}>Приглашение владельца</Title>
          {!token ? (
            <Alert color="red">
              Ссылка неполная (нет token). Откройте письмо или запросите новое приглашение у поддержки платформы.
            </Alert>
          ) : (
            <>
              <Text size="sm" c="dimmed">
                Задайте пароль для входа в админку клиники.
              </Text>
              <PasswordInput
                label="Пароль"
                value={password}
                onChange={(e) => setPassword(e.currentTarget.value)}
                autoComplete="new-password"
              />
              {err ? (
                <Alert color="red" title="Ошибка">
                  {err}
                </Alert>
              ) : null}
              <Button onClick={() => void submit()} loading={busy}>
                Сохранить и перейти ко входу
              </Button>
            </>
          )}
          <Text size="sm">
            <Link to={ROUTE_PATHS.marketing.landing}>← На главную</Link>
          </Text>
        </Stack>
      </Container>
    </Box>
  );
}
