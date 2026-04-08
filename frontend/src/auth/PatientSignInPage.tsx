import { SignInShell } from "@/auth/SignInShell";
import { PatientPhoneAuthPanel } from "@/auth/panels/PatientPhoneAuthPanel";
import { usePatientEntry } from "@/contexts/PatientEntryContext";
import { Stack, Text, Title } from "@mantine/core";

/**
 * Вход пациента только в контексте клиники (`/c/:clinicSlug/sign-in`).
 * Глобального «пациентского» URL нет — у каждой клиники свой slug.
 */
export default function PatientSignInPage() {
  const { clinicSlug } = usePatientEntry();

  return (
    <SignInShell>
      <Stack gap="lg">
        <div>
          <Title order={2}>Вход пациента</Title>
          <Text size="sm" c="dimmed" mt={6}>
            Личный кабинет клиники
            {clinicSlug ? (
              <>
                {" "}
                <Text span fw={600} component="span">
                  {clinicSlug}
                </Text>
              </>
            ) : null}
            . Введите телефон — отправим SMS с кодом.
          </Text>
        </div>
        <PatientPhoneAuthPanel />
      </Stack>
    </SignInShell>
  );
}
