import { useEffect, useMemo, useState } from "react";
import { Avatar, Button, Card, Group, Stack, Text, Textarea } from "@mantine/core";
import { ContextBar, QueryErrorAlert } from "@/shared/ui";
import { useMyStaffProfile, usePatchMyStaffProfile, useUploadMyStaffAvatar } from "@/hooks";

function initialsFromName(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() || "")
    .join("");
}

export default function AdminStaffCabinetPage() {
  const { data, isLoading, isError, error } = useMyStaffProfile();
  const patchMut = usePatchMyStaffProfile();
  const uploadMut = useUploadMyStaffAvatar();

  const [bio, setBio] = useState("");
  const [pickedFile, setPickedFile] = useState<File | null>(null);

  useEffect(() => {
    setBio(String(data?.bio ?? "").trim());
  }, [data?.bio]);

  const displayName = useMemo(() => {
    const n = String(data?.full_name ?? "").trim();
    return n || "Личный кабинет";
  }, [data?.full_name]);

  const avatarInitials = useMemo(() => initialsFromName(displayName) || "?", [displayName]);

  const canSaveBio = !isLoading && !patchMut.isPending && bio.trim() !== String(data?.bio ?? "").trim();
  const canUpload = Boolean(pickedFile) && !uploadMut.isPending;

  return (
    <Stack gap="md">
      <ContextBar title="Личный кабинет" breadcrumbs={<Text size="sm" c="dimmed">Фото профиля и «о себе».</Text>} />

      {isError ? <QueryErrorAlert error={error} /> : null}

      <Card withBorder radius="md" p="md">
        <Group align="center" wrap="nowrap">
          <Avatar src={data?.avatar_url ?? null} radius="xl" size={64} color="gray">
            {avatarInitials}
          </Avatar>
          <Stack gap={2} style={{ flex: 1 }}>
            <Text fw={800}>{displayName}</Text>
            <Text size="sm" c="dimmed">
              {data?.email || ""}
            </Text>
            <Text size="sm" c="dimmed">
              {data?.profession_category_name?.trim() || "Должность не указана"}
            </Text>
          </Stack>
          <input
            type="file"
            accept="image/*"
            style={{ display: "none" }}
            id="staff-avatar-input"
            onChange={(e) => {
              const f = e.currentTarget.files?.[0] ?? null;
              e.currentTarget.value = "";
              setPickedFile(f);
            }}
          />
          <Stack gap="xs">
            <Button
              variant="light"
              onClick={() => document.getElementById("staff-avatar-input")?.click()}
              disabled={uploadMut.isPending}
            >
              Выбрать фото
            </Button>
            <Button
              onClick={() => {
                if (!pickedFile) return;
                uploadMut.mutate(pickedFile, {
                  onSuccess: () => setPickedFile(null),
                });
              }}
              loading={uploadMut.isPending}
              disabled={!canUpload}
            >
              Загрузить
            </Button>
            {pickedFile ? (
              <Text size="xs" c="dimmed" lineClamp={1} style={{ maxWidth: 220 }}>
                {pickedFile.name}
              </Text>
            ) : null}
          </Stack>
        </Group>
      </Card>

      <Card withBorder radius="md" p="md">
        <Stack gap="sm">
          <Text fw={700}>О себе</Text>
          <Textarea
            minRows={5}
            placeholder="Например: чем вы занимаетесь в клинике, ваш опыт, график, специализация…"
            value={bio}
            onChange={(e) => setBio(e.currentTarget.value)}
            disabled={isLoading || patchMut.isPending}
          />
          <Group justify="flex-end">
            <Button
              onClick={() => patchMut.mutate({ bio: bio.trim() })}
              loading={patchMut.isPending}
              disabled={!canSaveBio}
            >
              Сохранить
            </Button>
          </Group>
          {patchMut.isError ? (
            <Text size="sm" c="red">
              {patchMut.error instanceof Error ? patchMut.error.message : "Не удалось сохранить"}
            </Text>
          ) : null}
          {uploadMut.isError ? (
            <Text size="sm" c="red">
              {uploadMut.error instanceof Error ? uploadMut.error.message : "Не удалось загрузить фото"}
            </Text>
          ) : null}
        </Stack>
      </Card>
    </Stack>
  );
}

