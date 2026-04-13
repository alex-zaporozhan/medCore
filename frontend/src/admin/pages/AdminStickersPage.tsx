import { Stack, Text } from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";

/** Управление стикерами: встроенный набор. */
export default function AdminStickersPage() {
  return (
    <Stack gap="md">
      <ContextBar title="Стикеры" />
      <Text c="dimmed" size="sm">
        Используется встроенный набор стикеров. В чате (пациент и админ) доступна кнопка «Стикер» для отправки стикера как сообщения.
      </Text>
      <Text size="sm">
        Кастомный набор стикеров (загрузка своих изображений) будет доступен в следующей версии.
      </Text>
    </Stack>
  );
}
