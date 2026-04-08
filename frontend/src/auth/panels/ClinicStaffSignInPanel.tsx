import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api, setAdminClinicId, setAdminId, setAdminToken } from "@/api/client";
import { queryKeys } from "@/queryKeys";
import { Alert, Button, Stack, Text, TextInput, Title } from "@mantine/core";
import { ROUTE_PATHS } from "@/routePaths";
import { defaultReturnToForTab, safeAuthReturnTo } from "@/auth/signInReturnTo";

const MIN_PASSWORD_LENGTH = 8;

export function ClinicStaffSignInPanel() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
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
      setError(err instanceof Error ? err.message : "Ошибка входа");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Stack gap="md">
      <div>
        <Title order={3}>Клиника: сотрудники и владелец</Title>
        <Text size="sm" c="dimmed" mt={6}>
          Войдите рабочим email и паролем. Роль владельца (owner) и права доступа назначаются в админке — отдельного
          входа для владельца не требуется.
        </Text>
      </div>
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
            autoComplete="username"
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
            autoComplete="current-password"
          />
          <Button type="submit" loading={loading} fullWidth>
            Войти в Business OS
          </Button>
        </Stack>
      </form>
      <Text size="sm" c="dimmed">
        <Link to={ROUTE_PATHS.marketing.landing}>На главную</Link>
      </Text>
    </Stack>
  );
}
