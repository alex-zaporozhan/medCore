import { Avatar, Badge, Button, Group, Skeleton, Stack, Text } from "@mantine/core";
import { GlassModal } from "./GlassModal";
import { useStaffProfile } from "@/hooks";
import dayjs from "dayjs";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";
import { displayPersonName } from "./personNameFallback";

export function StaffCardModal({
  opened,
  onClose,
  adminId,
}: {
  opened: boolean;
  onClose: () => void;
  adminId: string | null;
}) {
  const { data, isLoading, isError, error } = useStaffProfile(opened ? adminId : null);
  const title = displayPersonName(data?.full_name ?? null, adminId ?? "");
  const initials = String(title || "")
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((x) => x[0]?.toUpperCase())
    .join("");
  return (
    <GlassModal opened={opened} onClose={onClose} title={opened ? title : "Сотрудник"} size="md" padding="lg">
      <Stack gap="sm">
        {isLoading ? (
          <>
            <Skeleton height={18} width="70%" />
            <Skeleton height={14} width="55%" />
            <Skeleton height={14} width="45%" />
          </>
        ) : isError ? (
          <Text size="sm" c="red">
            {error instanceof Error ? error.message : "Не удалось загрузить карточку сотрудника"}
          </Text>
        ) : data ? (
          <>
            <Group gap="sm" wrap="nowrap" align="flex-start">
              <Avatar src={data.avatar_url ?? null} radius="xl" size={54} color="gray">
                {initials || "?"}
              </Avatar>
              <Stack gap={4} style={{ flex: 1 }}>
            <Group gap="xs" wrap="wrap">
              <Text fw={800} size="md">
                {displayPersonName(data.full_name, data.id)}
              </Text>
              {String(data.employment_status).toLowerCase() !== "active" ? (
                <Badge size="sm" color="gray" variant="light">
                  Не активен
                </Badge>
              ) : null}
            </Group>
            <Text size="sm" c="dimmed">
              {data.profession_category_name?.trim() || "Должность не указана"}
            </Text>
            {String(data.bio ?? "").trim() ? (
              <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                {String(data.bio ?? "").trim()}
              </Text>
            ) : (
              <Text size="sm" c="dimmed">
                О себе: —
              </Text>
            )}
            {data.birth_date ? (
              <Text size="sm" c="dimmed">
                Дата рождения: {dayjs(data.birth_date).format("DD.MM.YYYY")}
              </Text>
            ) : (
              <Text size="sm" c="dimmed">
                Дата рождения: —
              </Text>
            )}
            <Text size="xs" c="dimmed">
              {data.email}
            </Text>
              </Stack>
            </Group>
          </>
        ) : null}
        <Group justify="flex-end" mt="md">
          <Button
            component={Link}
            to={
              adminId
                ? `${ROUTE_PATHS.admin.staffChat}?dm_peer_id=${encodeURIComponent(adminId)}`
                : ROUTE_PATHS.admin.staffChat
            }
            variant="light"
            disabled={!adminId}
            onClick={onClose}
          >
            Написать сообщение
          </Button>
          <Button variant="default" onClick={onClose}>
            Закрыть
          </Button>
        </Group>
      </Stack>
    </GlassModal>
  );
}

