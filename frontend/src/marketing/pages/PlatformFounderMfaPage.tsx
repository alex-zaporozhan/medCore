import { SignInShell } from "@/auth/SignInShell";
import { PlatformFounderMfaPanel } from "@/auth/panels/PlatformFounderMfaPanel";
import { Stack, Text, Title } from "@mantine/core";

/**
 * Шаг 2 входа основателя: только TOTP после успешной проверки email/пароля.
 * Прямой URL: `/platform/login/mfa` (ожидается MFA-токен в sessionStorage после шага 1).
 */
export default function PlatformFounderMfaPage() {
  return (
    <SignInShell>
      <Stack gap="lg">
        <div>
          <Title order={2}>Двухфакторный вход</Title>
          <Text size="sm" c="dimmed" mt={6}>
            Шаг 2 из 2: код из приложения-аутентификатора (TOTP).
          </Text>
        </div>
        <PlatformFounderMfaPanel />
      </Stack>
    </SignInShell>
  );
}
