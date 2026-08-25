import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActionIcon,
  Avatar,
  Badge,
  Box,
  Button,
  Card,
  Divider,
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
import { useTranslation } from "react-i18next";
import { useUiLocale } from "@/i18n/useUiLocale";
import { ContextBar, EmptyState, PageSkeleton, QueryErrorAlert, PersonNameLink } from "@/shared/ui";
import { useAdminAdmins } from "@/hooks/useAdminAdmins";
import {
  useCreateStaffDmRoom,
  useCreateStaffGroupRoom,
  useMarkStaffChatRoomRead,
  usePostStaffChatMessage,
  useStaffChatMessages,
  useStaffChatRooms,
  useStaffTaskChatRoom,
  useUploadStaffChatAttachment,
  useInviteStaffRoomMember,
} from "@/hooks/useStaffCollab";
import { getAdminId } from "@/api/client";
import dayjs from "dayjs";
import {
  IconCheckbox,
  IconHash,
  IconMessageCircle,
  IconPaperclip,
  IconPhoto,
  IconUsers,
  IconVolume,
} from "@tabler/icons-react";
import { AppleEmojiRichText } from "@/shared/AppleEmojiRichText";
import { ClinicChatAttachments } from "@/shared/ClinicChatAttachments";
import { shouldOmitChatBodyForAudioAttachment } from "@/shared/chatMessageBodyDisplay";
import { EmojiMartPopoverPicker, AppleEmojiOverlayTextarea } from "@/shared/ui";
import { VoiceNoteRecorderButton } from "@/shared/ui/VoiceNoteRecorderButton";
import { api } from "@/api/client";
import { useAdminSession } from "@/hooks/useAdminSession";
import { adminChatIncomingBubbleStyle, adminChatOutgoingBubbleStyle } from "@/shared/adminChatChrome";
import { adminChatMessagesRegion } from "@/shared/chatI18n";
import { displayPersonName } from "@/shared/ui/personNameFallback";

export default function AdminStaffChatPage() {
  const { t } = useTranslation("chat");
  const { locale } = useUiLocale();
  const timeFormat = locale === "en" ? "MMM D, YYYY HH:mm" : "DD.MM.YYYY HH:mm";
  const { data: adminSession } = useAdminSession();
  const allowAudioAttachmentDownload = adminSession?.roles?.includes("owner") ?? false;

  const [searchParams] = useSearchParams();
  const taskIdFromUrl = searchParams.get("task");
  const dmPeerFromUrl = searchParams.get("dm_peer_id")?.trim() || null;

  const { data: rooms, isLoading: roomsLoading, isError: roomsErr, error: roomsError } =
    useStaffChatRooms();
  const { data: taskRoomFromUrl, isLoading: taskRoomLoading } = useStaffTaskChatRoom(taskIdFromUrl);
  const { data: admins = [] } = useAdminAdmins();
  const currentAdminId = getAdminId();

  const [roomId, setRoomId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const [roomSearch, setRoomSearch] = useState("");

  const [dmOpened, setDmOpened] = useState(false);
  const [dmPeerId, setDmPeerId] = useState<string | null>(null);
  const [staffFinderOpened, setStaffFinderOpened] = useState(false);
  const [staffFinderSearch, setStaffFinderSearch] = useState("");
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
      {t("staff.subtitle")}
    </Text>
  );

  const getStaffChatAttachmentBlob = useCallback(
    (attachmentId: string) => api.getBlob(`/v1/admin/staff/attachments/${attachmentId}/file`),
    []
  );

  const dmMut = useCreateStaffDmRoom();
  const groupMut = useCreateStaffGroupRoom();
  const inviteMut = useInviteStaffRoomMember(roomId);
  const markReadMut = useMarkStaffChatRoomRead();
  const [autoOpenedDmPeer, setAutoOpenedDmPeer] = useState<string | null>(null);

  const dmMutate = dmMut.mutate;
  const dmPending = dmMut.isPending;

  useEffect(() => {
    if (taskIdFromUrl && taskRoomFromUrl?.id) {
      setRoomId(taskRoomFromUrl.id);
    }
  }, [taskIdFromUrl, taskRoomFromUrl?.id]);

  // Deep-link: open/create DM room with a specific colleague.
  useEffect(() => {
    if (!dmPeerFromUrl) return;
    if (!currentAdminId) return;
    if (dmPeerFromUrl === currentAdminId) return;
    if (autoOpenedDmPeer === dmPeerFromUrl) return;
    if (dmPending) return;
    dmMutate(dmPeerFromUrl, {
      onSuccess: (room) => {
        setRoomId(room.id);
        setAutoOpenedDmPeer(dmPeerFromUrl);
        setDmOpened(false);
        setDmPeerId(null);
      },
      onError: () => {
        setAutoOpenedDmPeer(dmPeerFromUrl);
      },
    });
  }, [dmPeerFromUrl, currentAdminId, autoOpenedDmPeer, dmMutate, dmPending]);

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

  const title = useMemo(
    () => rooms?.find((r) => r.id === roomId)?.title ?? t("staff.fallbackTitle"),
    [rooms, roomId, t],
  );
  const currentRoom = useMemo(() => rooms?.find((r) => r.id === roomId), [rooms, roomId]);
  const canInvite = Boolean(
    currentRoom && (currentRoom.kind === "GROUP" || currentRoom.kind === "TASK")
  );

  const filteredRooms = useMemo(() => {
    const s = roomSearch.trim().toLowerCase();
    const items = rooms ?? [];
    if (!s) return items;
    return items.filter((r) => {
      const hay = `${r.title || ""} ${(r.last_message_preview || "")} ${(r.dm_peer?.full_name || "")}`.toLowerCase();
      return hay.includes(s);
    });
  }, [rooms, roomSearch]);

  const staffFinderRows = useMemo(() => {
    const s = staffFinderSearch.trim().toLowerCase();
    const base = admins.filter((a) => a.id !== currentAdminId);
    const rows = !s
      ? base
      : base.filter((a) => {
          const name = (a.full_name || "").toLowerCase();
          const email = (a.email || "").toLowerCase();
          return name.includes(s) || email.includes(s);
        });
    return rows.sort((a, b) => (a.full_name || a.email || "").localeCompare(b.full_name || b.email || ""));
  }, [admins, staffFinderSearch, currentAdminId]);

  const adminPeerOptions = useMemo(() => {
    return admins
      .filter((a) => a.id !== currentAdminId)
      .map((a) => ({
        value: a.id,
        label: displayPersonName(a.full_name?.trim() || a.email, a.id),
      }));
  }, [admins, currentAdminId]);

  const onSend = () => {
    const text = draft.trim();
    if ((!text && !pendingFile) || !roomId) return;
    setAttachError(null);
    const body = text;
    postMut.mutate(body, {
      onSuccess: async (msg) => {
        setDraft("");
        if (pendingFile) {
          try {
            await uploadMut.mutateAsync({ messageId: msg.id, file: pendingFile });
            setPendingFile(null);
          } catch (e) {
            const err = e as Error;
            setAttachError(err.message || t("errors.uploadFailed"));
          }
        }
      },
      onError: (e) => {
        const err = e as Error;
        setAttachError(err.message || t("errors.saveFailed"));
      },
    });
  };

  const onPickRoom = (rid: string) => {
    setRoomId(rid);
    markReadMut.mutate(rid);
  };

  const onCreateDm = () => {
    if (!dmPeerId) return;
    dmMut.mutate(dmPeerId, {
      onSuccess: (room) => {
        setRoomId(room.id);
        setDmOpened(false);
        setDmPeerId(null);
        markReadMut.mutate(room.id);
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
    const name = groupTitle.trim();
    if (!name || groupMembers.length < 1) return;
    groupMut.mutate(
      { title: name, member_admin_ids: groupMembers },
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
        <ContextBar title={t("staff.title")} />
        {staffChatSubtitle}
        <PageSkeleton variant="cards" cardsCount={2} />
      </Stack>
    );
  }

  if (roomsErr) {
    return (
      <Stack gap="md">
        <ContextBar title={t("staff.title")} />
        {staffChatSubtitle}
        <QueryErrorAlert error={roomsError} title={t("errors.loadFailed", { ns: "common" })} />
      </Stack>
    );
  }

  return (
    <Stack gap="md" style={{ height: "calc(100vh - 96px)", minHeight: 400 }}>
      <ContextBar title={t("staff.title")} />
      {staffChatSubtitle}

      {taskIdFromUrl && taskRoomLoading ? (
        <PageSkeleton variant="table" rows={2} />
      ) : null}

      {!rooms?.length ? (
        <EmptyState
          title={t("staff.emptyRoomsTitle")}
          description={t("staff.emptyRoomsHint")}
          action={{ label: t("staff.newGroup"), onClick: () => setGroupOpened(true) }}
        />
      ) : (
        <Group align="stretch" gap="md" wrap="wrap" style={{ flex: 1, minHeight: 0 }}>
          <Card
            withBorder
            radius="md"
            p="sm"
            w={{ base: "100%", md: 300 }}
            style={{ flexShrink: 0, display: "flex", flexDirection: "column", minHeight: 0 }}
          >
            <Stack gap="xs" style={{ flex: 1, minHeight: 0 }}>
              <Text size="xs" fw={600} c="dimmed" tt="uppercase">
                {t("staff.chats")}
              </Text>
              <TextInput
                size="xs"
                placeholder={t("staff.searchChats")}
                value={roomSearch}
                onChange={(e) => setRoomSearch(e.currentTarget.value)}
              />
              <Button size="xs" variant="light" onClick={() => setGroupOpened(true)}>
                {t("staff.newGroup")}
              </Button>
              <ScrollArea type="auto" style={{ flex: 1, minHeight: 0 }}>
                <Stack gap={6}>
                  {filteredRooms.length === 0 ? (
                    <Text size="xs" c="dimmed">
                      {t("staff.nothingFound")}
                    </Text>
                  ) : (
                    filteredRooms.map((r) => {
                      const selected = roomId === r.id;
                      const unread = Math.max(0, Number(r.unread_count ?? 0));
                      const icon =
                        r.kind === "GROUP" ? (
                          <IconUsers size={16} />
                        ) : r.kind === "TASK" ? (
                          <IconCheckbox size={16} />
                        ) : r.kind === "GENERAL" ? (
                          <IconHash size={16} />
                        ) : (
                          <IconMessageCircle size={16} />
                        );
                      const avatarUrl = r.kind === "DM" ? (r.dm_peer?.avatar_url ?? null) : null;
                      const avatarLabel = r.kind === "DM" ? (r.dm_peer?.full_name ?? r.title) : r.title;
                      const initials = String(avatarLabel || "")
                        .trim()
                        .split(/\s+/)
                        .slice(0, 2)
                        .map((x) => x[0]?.toUpperCase())
                        .join("");
                      const lastTime = r.last_message_at ? dayjs(r.last_message_at).format("HH:mm") : null;
                      return (
                        <Card
                          key={r.id}
                          withBorder={false}
                          radius="md"
                          p="xs"
                          style={{
                            cursor: "pointer",
                            background: selected ? "var(--mantine-color-gray-0)" : undefined,
                            border: selected ? "1px solid var(--mantine-color-gray-3)" : "1px solid transparent",
                          }}
                          onClick={() => onPickRoom(r.id)}
                        >
                          <Group gap="xs" wrap="nowrap" align="flex-start">
                            <Avatar src={avatarUrl} radius="xl" color="gray" size={34}>
                              {initials || "?"}
                            </Avatar>
                            <Box style={{ flex: 1, minWidth: 0 }}>
                              <Group justify="space-between" gap="xs" wrap="nowrap">
                                <Group gap={6} wrap="nowrap" style={{ minWidth: 0 }}>
                                  <Box style={{ color: "var(--mantine-color-gray-7)" }}>{icon}</Box>
                                  <Text size="sm" fw={600} lineClamp={1} style={{ flex: 1 }}>
                                    {r.title}
                                  </Text>
                                </Group>
                                <Text size="xs" c="dimmed">
                                  {lastTime ?? ""}
                                </Text>
                              </Group>
                              <Group justify="space-between" gap="xs" wrap="nowrap" mt={2}>
                                <Text size="xs" c="dimmed" lineClamp={1} style={{ flex: 1 }}>
                                  {r.last_message_preview?.trim() || "—"}
                                </Text>
                                {unread > 0 ? (
                                  <Badge size="sm" variant="filled" color="red" radius="xl">
                                    {unread}
                                  </Badge>
                                ) : null}
                              </Group>
                            </Box>
                          </Group>
                        </Card>
                      );
                    })
                  )}
                </Stack>
              </ScrollArea>
              <Divider my={4} />
              <Button size="xs" variant="light" onClick={() => setStaffFinderOpened(true)}>
                {t("staff.clinicStaff")}
              </Button>
            </Stack>
          </Card>

          <Card
            withBorder
            radius="md"
            p={0}
            style={{ flex: 1, minWidth: 280, display: "flex", flexDirection: "column" }}
          >
            {!roomId ? (
              <Box p="xl">
                <EmptyState
                  title={t("staff.pickTitle")}
                  description={t("staff.pickHint")}
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
                        {t("staff.invite")}
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
                      title={t("staff.emptyThreadTitle")}
                      description={t("staff.emptyThreadHint")}
                    />
                  ) : (
                    <Stack gap="sm" {...adminChatMessagesRegion()}>
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
                              <PersonNameLink kind="staff" id={m.author.id} label={m.author.full_name} size="sm" />
                              <Text size="xs" c="dimmed">
                                {dayjs(m.created_at).format(timeFormat)}
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
                      aria-label={t("staff.fileAria")}
                      onClick={() => triggerAttachPick()}
                    >
                      <IconPaperclip size={20} />
                    </ActionIcon>
                    <ActionIcon
                      variant="light"
                      size="lg"
                      aria-label={t("staff.photoAria")}
                      onClick={() => triggerAttachPick("image/*")}
                    >
                      <IconPhoto size={20} />
                    </ActionIcon>
                    <ActionIcon
                      variant="light"
                      size="lg"
                      aria-label={t("staff.audioAria")}
                      title={t("staff.audioTitle")}
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
                  {postMut.isError ? <QueryErrorAlert error={postMut.error} /> : null}
                  <AppleEmojiOverlayTextarea
                    ref={draftInputRef}
                    placeholder={t("staff.composerPlaceholder")}
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
                      {t("send")}
                    </Button>
                  </Group>
                  <Text size="xs" c="dimmed">
                    {t("staff.composerHint")}
                  </Text>
                </Stack>
              </>
            )}
          </Card>
        </Group>
      )}

      <Modal
        opened={dmOpened}
        onClose={() => {
          setDmOpened(false);
          dmMut.reset();
        }}
        title={t("staff.dmTitle")}
        centered
      >
        <Stack gap="sm">
          {dmMut.isError ? <QueryErrorAlert error={dmMut.error} /> : null}
          <Select
            label={t("staff.colleague")}
            placeholder={t("staff.pickColleague")}
            data={adminPeerOptions}
            value={dmPeerId}
            onChange={setDmPeerId}
            searchable
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDmOpened(false)}>
              {t("cancel")}
            </Button>
            <Button onClick={onCreateDm} loading={dmMut.isPending} disabled={!dmPeerId}>
              {t("staff.openChat")}
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={staffFinderOpened}
        onClose={() => {
          setStaffFinderOpened(false);
          dmMut.reset();
        }}
        title={t("staff.clinicStaff")}
        centered
      >
        <Stack gap="sm">
          {dmMut.isError ? <QueryErrorAlert error={dmMut.error} /> : null}
          <TextInput
            placeholder={t("staff.searchNameEmail")}
            value={staffFinderSearch}
            onChange={(e) => setStaffFinderSearch(e.currentTarget.value)}
          />
          <ScrollArea h={320} type="auto">
            <Stack gap={6}>
              {staffFinderRows.length === 0 ? (
                <Text size="sm" c="dimmed">
                  {t("staff.nothingFound")}
                </Text>
              ) : (
                staffFinderRows.map((a) => {
                  const label = displayPersonName(a.full_name?.trim() || a.email, a.id);
                  const initials = label
                    .trim()
                    .split(/\s+/)
                    .slice(0, 2)
                    .map((x) => x[0]?.toUpperCase())
                    .join("");
                  return (
                    <Card
                      key={a.id}
                      p="xs"
                      radius="md"
                      withBorder
                      style={{ cursor: "pointer" }}
                      onClick={() => {
                        dmMut.mutate(a.id, {
                          onSuccess: (room) => {
                            setStaffFinderOpened(false);
                            setStaffFinderSearch("");
                            setRoomId(room.id);
                            markReadMut.mutate(room.id);
                          },
                        });
                      }}
                    >
                      <Group gap="sm" wrap="nowrap">
                        <Avatar radius="xl" color="gray" size={34}>
                          {initials || "?"}
                        </Avatar>
                        <Box style={{ flex: 1, minWidth: 0 }}>
                          <Text fw={600} size="sm" lineClamp={1}>
                            {label}
                          </Text>
                          <Text size="xs" c="dimmed" lineClamp={1}>
                            {a.email || ""}
                          </Text>
                        </Box>
                        <Button
                          size="xs"
                          variant="light"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                          }}
                        >
                          {t("staff.write")}
                        </Button>
                      </Group>
                    </Card>
                  );
                })
              )}
            </Stack>
          </ScrollArea>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setStaffFinderOpened(false)}>
              {t("close")}
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={inviteOpened}
        onClose={() => {
          setInviteOpened(false);
          inviteMut.reset();
        }}
        title={t("staff.inviteTitle")}
        centered
      >
        <Stack gap="sm">
          {inviteMut.isError ? <QueryErrorAlert error={inviteMut.error} /> : null}
          <Text size="sm" c="dimmed">
            {t("staff.inviteHint")}
          </Text>
          <Select
            label={t("staff.colleague")}
            placeholder={t("staff.pickColleague")}
            data={adminPeerOptions}
            value={invitePeerId}
            onChange={setInvitePeerId}
            searchable
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setInviteOpened(false)}>
              {t("cancel")}
            </Button>
            <Button onClick={onInviteMember} loading={inviteMut.isPending} disabled={!invitePeerId}>
              {t("staff.invite")}
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={groupOpened}
        onClose={() => {
          setGroupOpened(false);
          groupMut.reset();
        }}
        title={t("staff.groupTitle")}
        centered
      >
        <Stack gap="sm">
          {groupMut.isError ? <QueryErrorAlert error={groupMut.error} /> : null}
          <Text size="sm" c="dimmed">
            {t("staff.groupHint")}
          </Text>
          <TextInput
            label={t("staff.groupName")}
            placeholder={t("staff.groupNamePlaceholder")}
            value={groupTitle}
            onChange={(e) => setGroupTitle(e.currentTarget.value)}
          />
          <MultiSelect
            label={t("staff.members")}
            placeholder={t("staff.pickColleagues")}
            data={adminPeerOptions}
            value={groupMembers}
            onChange={setGroupMembers}
            searchable
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setGroupOpened(false)}>
              {t("cancel")}
            </Button>
            <Button
              onClick={onCreateGroup}
              loading={groupMut.isPending}
              disabled={!groupTitle.trim() || groupMembers.length < 1}
            >
              {t("create")}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
