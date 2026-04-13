import { SignInShell } from "@/auth/SignInShell";
import { ClinicStaffSignInPanel } from "@/auth/panels/ClinicStaffSignInPanel";
import {
  Alert,
  Button,
  Divider,
  Group,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

export default function PublicLoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [patientSlug, setPatientSlug] = useState("");

  const patientEntryHint = useMemo(() => {
    const v = searchParams.get("patientEntry");
    if (v === "need-clinic") {
      return "Войдите по ссылке вашей клиники или укажите адрес клиники ниже (как в ссылке …/c/адрес-клиники/…).";
    }
    if (v === "patient-url-needs-clinic-slug") {
      return "В ссылке для входа пациента должен быть адрес клиники: /c/ваш-slug/sign-in (три части пути после домена), а не /c/sign-in.";
    }
    if (v === "session-expired") {
      return "Сессия истекла. Войдите снова по ссылке клиники.";
    }
    if (v === "oauth-cancelled" || v === "oauth-error") {
      return "Вход через соцсеть прерван или не удался. Используйте ссылку клиники и вход по телефону.";
    }
    return null;
  }, [searchParams]);

  const goPatientBySlug = () => {
    const raw = patientSlug.trim().replace(/^\/+|\/+$/g, "");
    if (!raw) return;
    const slug = raw.replace(/^c\//i, "").split("/")[0]?.trim();
    if (!slug) return;
    navigate(`/c/${encodeURIComponent(slug)}/sign-in`);
  };

  return (
    <SignInShell>
      <Stack gap="xl">
        <div>
          <Title order={2}>Вход</Title>
          <Text size="sm" c="dimmed" mt={6}>
            Пациенты — по адресу клиники. Сотрудники и владелец — email и пароль ниже.
          </Text>
        </div>

        {patientEntryHint ? (
          <Alert color="slate" variant="light" title="Вход для пациентов">
            {patientEntryHint}
          </Alert>
        ) : null}

        <Stack gap="sm">
          <Text size="sm" fw={600}>
            Пациентам
          </Text>
          <Text size="xs" c="dimmed">
            У каждой клиники свой адрес в ссылке. Вставьте адрес из приглашения (поддомен / путь после{" "}
            <Text span ff="monospace">
              /c/
            </Text>
            ).
          </Text>
          <Text size="xs" c="dimmed">
            Для владельца клиники: в поле ниже можно ввести тот же <Text span fw={600}>Slug клиники</Text> (для
            публичных URL), который задаётся в админке в разделе{" "}
            <Text span fw={600}>
              Настройки → Клиники → редактировать клинику
            </Text>
            . Там же при необходимости можно изменить отображаемое название клиники; slug влияет на ссылку вида{" "}
            <Text span ff="monospace">
              …/c/ваш-slug/sign-in
            </Text>
            .
          </Text>
          <Group gap="xs" align="flex-end" wrap="nowrap">
            <TextInput
              flex={1}
              label="Адрес клиники"
              placeholder="например demo-clinic"
              value={patientSlug}
              onChange={(e) => setPatientSlug(e.currentTarget.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") goPatientBySlug();
              }}
            />
            <Button variant="filled" color="slate" onClick={goPatientBySlug}>
              Войти
            </Button>
          </Group>
        </Stack>

        <Divider label="Сотрудники клиники" labelPosition="center" />

        <ClinicStaffSignInPanel />
      </Stack>
    </SignInShell>
  );
}
