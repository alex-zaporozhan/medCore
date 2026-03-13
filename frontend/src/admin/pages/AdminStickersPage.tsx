import { Stack, Text, Title } from "@mantine/core";

/** Stickers management. MVP — built-in set only. */
export default function AdminStickersPage() {
  return (
    <Stack gap="md">
      <Title order={3}>Стикеры</Title>
      <Text c="dimmed" size="sm">
        Используется встроенный набор стикеров. В чате (пациент и админ) доступна кнопка «Стикер» для отправки стикера как сообщения.
      </Text>
      <Text size="sm">
        Кастомный набор стикеров (загрузка своих изображений) будет доступен в следующей версии.
      </Text>
    </Stack>
  );
}
