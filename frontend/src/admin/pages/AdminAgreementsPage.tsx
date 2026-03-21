import { useAdminClinic } from "@/contexts/AdminClinicContext";
import {
  useAdminAgreementSettings,
  useUpdateAdminAgreementSettingsMutation,
} from "@/hooks/useAdminAgreements";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Button,
  Stack,
  Switch,
  Text,
  Textarea,
} from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";
import { QueryErrorAlert } from "@/shared/ui";
import { useState, useEffect } from "react";

export default function AdminAgreementsPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;

  const { data, isLoading, isError, error } = useAdminAgreementSettings(clinicId);

  const [pdText, setPdText] = useState("");
  const [allowWithoutMailing, setAllowWithoutMailing] = useState(true);

  useEffect(() => {
    if (data) {
      setPdText(data.pd_agreement_text ?? "");
      setAllowWithoutMailing(data.allow_registration_without_mailing_consent);
    }
  }, [data?.clinic_id, data?.pd_agreement_text, data?.allow_registration_without_mailing_consent]);

  const saveMutation = useUpdateAdminAgreementSettingsMutation(clinicId);

  if (!clinicId) {
    return (
      <Stack>
        <ContextBar title="Соглашения" />
        <EmptyStateHint title="Выберите клинику" />
      </Stack>
    );
  }

  if (isLoading) {
    return (
      <Stack>
        <ContextBar title="Соглашения" />
        <Text c="dimmed">Загрузка...</Text>
      </Stack>
    );
  }

  if (isError) {
    return (
      <Stack>
        <ContextBar title="Соглашения" />
        <QueryErrorAlert error={error} title="Не удалось загрузить настройки" />
      </Stack>
    );
  }

  return (
    <Stack>
      <ContextBar title="Соглашения" />
      <Text size="sm" c="dimmed">
        Текст соглашения на обработку ПД показывается при регистрации. Разрешение регистрации без согласия на рассылку определяет, обязательна ли вторая галочка.
      </Text>
      <Textarea
        label="Текст соглашения на обработку персональных данных"
        placeholder="Введите текст политики..."
        value={pdText}
        onChange={(e) => setPdText(e.currentTarget.value)}
        minRows={6}
      />
      <Switch
        label="Разрешить регистрацию без согласия на рассылку"
        description="Нет — пациент не сможет завершить регистрацию без галочки «рассылка». Да — можно зарегистрироваться без рассылки."
        checked={allowWithoutMailing}
        onChange={(e) => setAllowWithoutMailing(e.currentTarget.checked)}
      />
      <Button
        onClick={() =>
          saveMutation.mutate({
            pd_agreement_text: pdText || null,
            allow_registration_without_mailing_consent: allowWithoutMailing,
          })
        }
        loading={saveMutation.isPending}
      >
        Сохранить
      </Button>
    </Stack>
  );
}
