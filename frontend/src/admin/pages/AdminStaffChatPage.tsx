import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActionIcon,
  Box,
  Button,
  Card,
  Group,
  Modal,
  MultiSelect,
  ScrollArea,
  Select,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { useSearchParams } from "react-router-dom";
import { ContextBar, EmptyState, PageSkeleton, QueryErrorAlert } from "@/shared/ui";
import { useAdminAdmins } from "@/hooks/useAdminAdmins";
import {
  useCreateStaffDmRoom,
  useCreateStaffGroupRoom,
  usePostStaffChatMessage,
  useStaffChatMessages,
  useStaffChatRooms,
  useStaffTaskChatRoom,
  useUploadStaffChatAttachment,
  useInviteStaffRoomMember,
} from "@/hooks/useStaffCollab";
import type { StaffChatRoomResponse } from "@/hooks/useStaffCollab";
import { getAdminId } from "@/api/client";
import dayjs from "dayjs";
import { IconPaperclip, IconPhoto, IconVolume } from "@tabler/icons-react";
import { AppleEmojiRichText } from "@/shared/AppleEmojiRichText";
import { ClinicChatAttachments } from "@/shared/ClinicChatAttachments";
import { shouldOmitChatBodyForAudioAttachment } from "@/shared/chatMessageBodyDisplay";
import { EmojiMartPopoverPicker, AppleEmojiOverlayTextarea } from "@/shared/ui";
import { VoiceNoteRecorderButton } from "@/shared/ui/VoiceNoteRecorderButton";
import { api } from "@/api/client";
import { useAdminSession } from "@/hooks/useAdminSession";
import { ADMIN_CHAT_MESSAGES_REGION, adminChatIncomingBubbleStyle, adminChatOutgoingBubbleStyle } from "@/shared/adminChatChrome";

function staffRoomSelectLabel(r: StaffChatRoomResponse): string {
  const k = r.kind;
  if (k === "GENERAL") return `Общий · ${r.title || "канал"}`;
  if (k === "DM") return `Личные · ${r.title}`;
  if (k === "GROUP") return `Группа · ${r.title}`;
  if (k === "TASK") return r.title || "Задача";
  return r.title || r.id.slice(0, 8);
}

export default function AdminStaffChatPage() {
  const { data: adminSession } = useAdminSession();
  const allowAudioAttachmentDownload = adminSession?.roles?.includes("owner") ?? false;

  const [searchParams] = useSearchParams();
  const taskIdFromUrl = searchParams.get("task");

  const { data: rooms, isLoading: roomsLoading, isError: roomsErr, error: roomsError } =
    useStaffChatRooms();
  const { data: taskRoomFromUrl, isLoading: taskRoomLoading } = useStaffTaskChatRoom(taskIdFromUrl);
  const { data: admins = [] } = useAdminAdmins();
  const currentAdminId = getAdminId();

  const [roomId, setRoomId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);

  const [dmOpened, setDmOpened] = useState(false);
  const [dmPeerId, setDmPeerId] = useState<string | null>(null);
  const [groupOpened, setGroupOpened] = useState(false);
  const [groupTitle, setGroupTitle] = useState("");
  const [groupMembers, setGroupMembers] = useState<string[]>([]);
  const [inviteOpened, setInviteOpened] = useState(false);
  const [invitePeerId, setInvitePeerId] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const attachFileRef = useRef<HTMLInputElement>(null);
  const draftInputRef = useRef<HTMLTextAreaElement>(null);

  const triggerAttachPick = useCallback((accept?: string) => {
    const el = attachFileRef.current;
    if (!el) return;
    el.accept = accept ?? "";
    el.value = "";
    el.click();
  }, []);

  const staffChatSubtitle = (
    <Text size="sm" c="dimmed" maw={720} lh={1.4}>
      Внутренний чат клиники (без сторонних мессенджеров). Текст, файлы и{" "}
      <strong>голосовые</strong> — кнопка микрофона или файл аудио. Видео-кружки не используются.
    </Text>
  );

  const getStaffChatAttachmentBlob = useCallback(
    (attachmentId: string) => api.getBlob(`/v1/admin/staff/attachments/${attachmentId}/file`),
    []
  );

  const dmMut = useCreateStaffDmRoom();
  const groupMut = useCreateStaffGroupRoom();
  const inviteMut = useInviteStaffRoomMember(roomId);

  useEffect(() => {
    if (taskIdFromUrl && taskRoomFromUrl?.id) {
      setRoomId(taskRoomFromUrl.id);
    }
  }, [taskIdFromUrl, taskRoomFromUrl?.id]);

  const {
    data: messages,
    isLoading: msgLoading,
    isError: msgErr,
    error: msgError,
  } = useStaffChatMessages(roomId);

  const postMut = usePostStaffChatMessage(roomId);
  const uploadMut = useUploadStaffChatAttachment(roomId);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages?.length, roomId]);

  const title = useMemo(() => rooms?.find((r) => r.id === roomId)?.title ?? "Чат персонала", [rooms, roomId]);
  const currentRoom = useMemo(() => rooms?.find((r) => r.id === roomId), [rooms, roomId]);
  const canInvite = Boolean(
    currentRoom && (currentRoom.kind === "GROUP" || currentRoom.kind === "TASK")
  );

  const adminPeerOptions = useMemo(() => {
    return admins
      .filter((a) => a.id !== currentAdminId)
      .map((a) => ({
        value: a.id,
        label: a.full_name?.trim() || a.email || a.id.slice(0, 8),
      }));
  }, [admins, currentAdminId]);

  const onSend = () => {
    const t = draft.trim();
    if ((!t && !pendingFile) || !roomId) return;
    setAttachError(null);
    const body = t;
    postMut.mutate(body, {
      onSuccess: async (msg) => {
        setDraft("");
        if (pendingFile) {
          try {
            await uploadMut.mutateAsync({ messageId: msg.id, file: pendingFile });
            setPendingFile(null);
          } catch (e) {
            const err = e as Error;
            setAttachError(err.message || "Не удалось загрузить файл");
          }
        }
      },
    });
  };

  const onCreateDm = () => {
    if (!dmPeerId) return;
    dmMut.mutate(dmPeerId, {
      onSuccess: (room) => {
        setRoomId(room.id);
        setDmOpened(false);
        setDmPeerId(null);
      },
    });
  };

  const onInviteMember = () => {
    if (!invitePeerId) return;
    inviteMut.mutate(invitePeerId, {
      onSuccess: () => {
        setInviteOpened(false);
        setInvitePeerId(null);
      },
    });
  };

  const onCreateGroup = () => {
    const t = groupTitle.trim();
    if (!t || groupMembers.length < 1) return;
    groupMut.mutate(
      { title: t, member_admin_ids: groupMembers },
      {
        onSuccess: (room) => {
          setRoomId(room.id);
          setGroupOpened(false);
          setGroupTitle("");
          setGroupMembers([]);
        },
      }
    );
  };

  if (roomsLoading) {
    return (
      <Stack gap="md">
        <ContextBar title="Чат команды" breadcrumbs={staffChatSubtitle} />
        <PageSkeleton variant="cards" cardsCount={2} />
      </Stack>
    );
  }

  if (roomsErr) {
    return (
      <Stack gap="md">
        <ContextBar title="Чат команды" breadcrumbs={staffChatSubtitle} />
        <QueryErrorAlert error={roomsError} />
      </Stack>
    );
  }

  return (
    <Stack gap="md" style={{ height: "calc(100vh - 96px)", minHeight: 400 }}>
      <ContextBar title="Чат команды" breadcrumbs={staffChatSubtitle} />

      {taskIdFromUrl && taskRoomLoading ? (
        <PageSkeleton variant="table" rows={2} />
      ) : null}

      {!rooms?.length ? (
        <EmptyState title="Нет комнат" description="Не удалось загрузить каналы чата." />
      ) : (
        <Group align="stretch" gap="md" wrap="nowrap" style={{ flex: 1, minHeight: 0 }}>
          <Card
            withBorder
            radius="md"
            p="sm"
            style={{ width: 300, flexShrink: 0, display: "flex", flexDirection: "column" }}
          >
            <Stack gap="xs">
              <Text size="xs" fw={600} c="dimmed" tt="uppercase">
                Чаты
              </Text>
              <Button size="xs" variant="light" onClick={() => setDmOpened(true)}>
                Найти / личный чат
              </Button>
              <Button size="xs" variant="light" onClick={() => setGroupOpened(true)}>
                Новая группа
              </Button>
              <ScrollArea h={220} type="auto">
                <Stack gap={4}>
                  {(rooms ?? []).map((r) => (
                    <Button
                      key={r.id}
                      size="xs"
                      variant={roomId === r.id ? "filled" : "subtle"}
                      justify="flex-start"
                      onClick={() => setRoomId(r.id)}
                    >
                      {staffRoomSelectLabel(r)}
                    </Button>
                  ))}
                </Stack>
              </ScrollArea>
              <Text size="xs" fw={600} c="dimmed" tt="uppercase">
                Персонал клиники
              </Text>
              <ScrollArea h={160} type="auto">
                <Stack gap={4}>
                  {adminPeerOptions.map((o) => (
                    <Text key={o.value} size="xs" c="dimmed">
                      {o.label}
                    </Text>
                  ))}
                </Stack>
              </ScrollArea>
            </Stack>
          </Card>

          <Card
            withBorder
            radius="md"
            p={0}
            style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}
          >
            {!roomId ? (
              <Box p="xl">
                <EmptyState
                  title="Выберите чат"
                  description="Слева — история комнат и список коллег. Откройте личный чат или канал, чтобы писать сообщения."
                />
              </Box>
            ) : (
              <>
                <Group justify="space-between" px="md" py="xs" wrap="wrap" style={{ borderBottom: "1px solid var(--mantine-color-gray-3)" }}>
                  <Text size="sm" fw={600}>
                    {title}
                  </Text>
                  <Group gap="xs">
                    {canInvite ? (
                      <Button size="xs" variant="outline" onClick={() => setInviteOpened(true)}>
                        Пригласить
                      </Button>
                    ) : null}
                  </Group>
                </Group>
                <ScrollArea style={{ flex: 1 }} p="md" type="auto">
                  {msgLoading ? (
                    <PageSkeleton variant="table" rows={4} />
                  ) : msgErr ? (
                    <QueryErrorAlert error={msgError} />
                  ) : !messages?.length ? (
                    <EmptyState
                      title="Пока пусто"
                      description="Напишите сообщение или запишите голос (микрофон). Файл или фото — иконками; вложение добавляется к последнему отправленному тексту."
                    />
                  ) : (
                    <Stack gap="sm" {...ADMIN_CHAT_MESSAGES_REGION}>
                      {messages.map((m) => {
                        const isMine = m.author.id === currentAdminId;
                        const audioMinW = (m.attachments ?? []).some((a) =>
                          (a.content_type || "").toLowerCase().startsWith("audio/")
                        )
                          ? 280
                          : undefined;
                        return (
                          <Box
                            key={m.id}
                            px="xs"
                            py="xs"
                            style={{
                              alignSelf: isMine ? "flex-end" : "flex-start",
                              maxWidth: "80%",
                              minWidth: audioMinW,
                              ...(isMine ? adminChatOutgoingBubbleStyle() : adminChatIncomingBubbleStyle()),
                            }}
                          >
                            <Group justify="space-between" mb={4} wrap="nowrap" gap="xs">
                              <Text size="sm" fw={600}>
                                {m.author.full_name?.trim() || "Сотрудник"}
                              </Text>
                              <Text size="xs" c="dimmed">
                                {dayjs(m.created_at).format("DD.MM.YYYY HH:mm")}
                              </Text>
                            </Group>
                            {shouldOmitChatBodyForAudioAttachment(m.body, m.attachments ?? []) ? null : (
                              <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                                <AppleEmojiRichText text={m.body} />
                              </Text>
                            )}
                            {(m.attachments ?? []).length > 0 ? (
                              <ClinicChatAttachments
                                attachments={m.attachments ?? []}
                                getBlob={getStaffChatAttachmentBlob}
                                allowAudioAttachmentDownload={allowAudioAttachmentDownload}
                              />
                            ) : null}
                          </Box>
                        );
                      })}
                      <div ref={bottomRef} />
                    </Stack>
                  )}
                </ScrollArea>
                <Stack gap="xs" p="md" style={{ borderTop: "1px solid var(--mantine-color-gray-3)" }}>
                  <input
                    ref={attachFileRef}
                    type="file"
                    style={{ display: "none" }}
                    onChange={(e) => {
                      const f = e.target.files?.[0] ?? null;
                      setPendingFile(f);
                      setAttachError(null);
                      e.target.value = "";
                    }}
                  />
                  <Group gap="xs">
                    <ActionIcon
                      variant="light"
                      size="lg"
                      aria-label="Файл"
                      onClick={() => triggerAttachPick()}
                    >
                      <IconPaperclip size={20} />
                    </ActionIcon>
                    <ActionIcon
                      variant="light"
                      size="lg"
                      aria-label="Фото"
                      onClick={() => triggerAttachPick("image/*")}
                    >
                      <IconPhoto size={20} />
                    </ActionIcon>
                    <ActionIcon
                      variant="light"
                      size="lg"
                      aria-label="Аудио файл"
                      title="Выбрать аудиофайл (без видео)"
                      onClick={() => triggerAttachPick("audio/*")}
                    >
                      <IconVolume size={20} />
                    </ActionIcon>
                    <VoiceNoteRecorderButton
                      disabled={postMut.isPending || uploadMut.isPending}
                      onError={(msg) => setAttachError(msg)}
                      onRecorded={(file) => {
                        setAttachError(null);
                        setPendingFile(file);
                      }}
                    />
                    <EmojiMartPopoverPicker
                      actionIconProps={{ variant: "light", size: "lg", color: "gray" }}
                      onPick={(native) => setDraft((prev) => prev + native)}
                      onInserted={() => draftInputRef.current?.focus()}
                    />
                    {pendingFile ? (
                      <Text size="xs" c="dimmed" lineClamp={1} style={{ flex: 1 }}>
                        {pendingFile.name}
                      </Text>
                    ) : null}
                  </Group>
                  {attachError ? (
                    <Text size="xs" c="red">
                      {attachError}
                    </Text>
                  ) : null}
                  <AppleEmojiOverlayTextarea
                    ref={draftInputRef}
                    placeholder="Сообщение…"
                    minRows={2}
                    value={draft}
                    onChange={(e) => setDraft(e.currentTarget.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                        e.preventDefault();
                        onSend();
                      }
                    }}
                  />
                  <Group justify="flex-end">
                    <Button
                      onClick={onSend}
                      loading={postMut.isPending || uploadMut.isPending}
                      disabled={!draft.trim() && !pendingFile}
                    >
                      Отправить
                    </Button>
                  </Group>
                  <Text size="xs" c="dimmed">
                    Ctrl+Enter — отправить. Голос — микрофоном или файлом аудио; вложение к последнему отправленному
                    сообщению.
                  </Text>
                </Stack>
              </>
            )}
          </Card>
        </Group>
      )}

      <Modal opened={dmOpened} onClose={() => setDmOpened(false)} title="Личный чат" centered>
        <Stack gap="sm">
          <Select
            label="Сотрудник"
            placeholder="Выберите коллегу"
            data={adminPeerOptions}
            value={dmPeerId}
            onChange={setDmPeerId}
            searchable
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDmOpened(false)}>
              Отмена
            </Button>
            <Button onClick={onCreateDm} loading={dmMut.isPending} disabled={!dmPeerId}>
              Открыть чат
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={inviteOpened} onClose={() => setInviteOpened(false)} title="Пригласить в комнату" centered>
        <Stack gap="sm">
          <Text size="sm" c="dimmed">
            Доступно для групп и чатов по задаче. Участником может стать только сотрудник этой клиники.
          </Text>
          <Select
            label="Сотрудник"
            placeholder="Выберите коллегу"
            data={adminPeerOptions}
            value={invitePeerId}
            onChange={setInvitePeerId}
            searchable
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setInviteOpened(false)}>
              Отмена
            </Button>
            <Button onClick={onInviteMember} loading={inviteMut.isPending} disabled={!invitePeerId}>
              Пригласить
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={groupOpened} onClose={() => setGroupOpened(false)} title="Новая группа" centered>
        <Stack gap="sm">
          <Text size="sm" c="dimmed">
            Вы и выбранные участники будут добавлены в группу.
          </Text>
          <TextInput
            label="Название группы"
            placeholder="Например: Смена 1"
            value={groupTitle}
            onChange={(e) => setGroupTitle(e.currentTarget.value)}
          />
          <MultiSelect
            label="Участники"
            placeholder="Выберите коллег"
            data={adminPeerOptions}
            value={groupMembers}
            onChange={setGroupMembers}
            searchable
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setGroupOpened(false)}>
              Отмена
            </Button>
            <Button
              onClick={onCreateGroup}
              loading={groupMut.isPending}
              disabled={!groupTitle.trim() || groupMembers.length < 1}
            >
              Создать
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
