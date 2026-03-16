import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "@/api/client";
import { setAdminToken, setAdminId } from "@/api/client";
import { Alert, Button, Paper, Stack, Text, TextInput, Title } from "@mantine/core";

const MIN_PASSWORD_LENGTH = 8;

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Пароль должен быть не менее ${MIN_PASSWORD_LENGTH} символов`);
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await api.post<{ access_token: string; admin_id: string; clinic_id: string; full_name: string | null }>(
        "/v1/admin/auth/login",
        { email: email.trim().toLowerCase(), password }
      );
      setAdminToken(res.access_token);
      if (res.admin_id) setAdminId(res.admin_id);
      navigate("/admin", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка входа");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Stack align="center" justify="center" style={{ minHeight: "100vh", background: "var(--bg-main)" }}>
      <Paper p="xl" radius="lg" shadow="sm" maw={400} w="100%" withBorder>
        <Stack gap="md">
          <Title order={3}>Вход в админку</Title>
          <Text size="sm" c="dimmed">
            Пароль не менее {MIN_PASSWORD_LENGTH} символов. Данные передаются по защищённому соединению.
          </Text>
          <form onSubmit={handleSubmit}>
            <Stack gap="md">
              {error && (
                <Alert color="red" title="Ошибка" onClose={() => setError(null)} withCloseButton>
                  {error}
                </Alert>
              )}
              <TextInput
                label="Email"
                type="email"
                placeholder="admin@example.com"
                value={email}
                onChange={(e) => setEmail(e.currentTarget.value)}
                required
              />
              <TextInput
                label="Пароль"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.currentTarget.value)}
                required
                minLength={MIN_PASSWORD_LENGTH}
                description={`Минимум ${MIN_PASSWORD_LENGTH} символов`}
              />
              <Button type="submit" loading={loading} fullWidth>
                Войти
              </Button>
            </Stack>
          </form>
          <Text size="sm" c="dimmed">
            <Link to="/">На главную</Link>
          </Text>
        </Stack>
      </Paper>
    </Stack>
  );
}
