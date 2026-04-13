import { SignInShell } from "@/auth/SignInShell";
import { PlatformFounderSignInPanel } from "@/auth/panels/PlatformFounderSignInPanel";
import { Stack, Text, Title } from "@mantine/core";

/**
 * Скрытый вход основателя платформы (не в общем меню маркетинга).
 * Прямой URL: `/platform/login`.
 */
export default function PlatformFounderLoginPage() {
  return (
    <SignInShell>
      <Stack gap="lg">
        <div>
          <Title order={2}>Основатель платформы</Title>
          <Text size="sm" c="dimmed" mt={6}>
            Отдельный контур и JWT. Не путайте с входом в админку организации.
          </Text>
        </div>
        <PlatformFounderSignInPanel />
      </Stack>
    </SignInShell>
  );
}
