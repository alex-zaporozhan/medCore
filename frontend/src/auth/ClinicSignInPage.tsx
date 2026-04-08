import { SignInShell } from "@/auth/SignInShell";
import { ClinicStaffSignInPanel } from "@/auth/panels/ClinicStaffSignInPanel";
import { Stack, Text, Title } from "@mantine/core";

/** Вход сотрудников и владельца клиники (Business OS). Отдельно от пациента и основателя. */
export default function ClinicSignInPage() {
  return (
    <SignInShell>
      <Stack gap="lg">
        <div>
          <Title order={2}>Вход в Business OS</Title>
          <Text size="sm" c="dimmed" mt={6}>
            Рабочий email и пароль клиники. После входа доступ к разделам определяется ролями.
          </Text>
        </div>
        <ClinicStaffSignInPanel />
      </Stack>
    </SignInShell>
  );
}
