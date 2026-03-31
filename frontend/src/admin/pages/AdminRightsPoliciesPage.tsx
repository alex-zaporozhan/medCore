import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  Collapse,
  Divider,
  Group,
  Modal,
  MultiSelect,
  ScrollArea,
  Select,
  Stack,
  Switch,
  Table,
  Tabs,
  Text,
  TextInput,
  Tooltip,
  SegmentedControl,
  Paper,
  ThemeIcon,
  type ComboboxItem,
} from "@mantine/core";
import { IconBook, IconInfoCircle, IconPlus, IconShieldCheck } from "@tabler/icons-react";
import { getAdminId } from "@/api/client";
import {
  type UiLocale,
  getDomainGlossary,
  getDomainPlainSelectLabel,
  getDomainPrimaryLabel,
} from "@/admin/rbacDomainGlossary";
import { downloadUtf8Csv } from "@/admin/rbacCsvExport";
import {
  getPolicyFieldLabel,
  getRbacRightsPoliciesCopy,
  getRolePresetOptionLabel,
  rbacTooltipStyles,
} from "@/admin/rbacRightsPoliciesPageCopy";
import {
  useCreateClinicRole,
  useDeleteClinicRole,
  usePatchRbacPolicies,
  usePatchRolePermissions,
  usePatchUserPermissions,
  usePatchUserRoles,
  useRbacAudit,
  useRbacCatalog,
  useRbacPolicies,
  useRbacUsers,
} from "@/hooks";
import { useAdminSession } from "@/hooks/useAdminSession";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { ContextBar, PageSkeleton, QueryErrorAlert } from "@/shared/ui";
import { ADMIN_PERM_RBAC_MANAGE } from "@/shared/adminPermissions";
import type { RbacPermissionRead } from "@/hooks/useAdminRbacManagement";

function sortedUnique(values: string[]): string[] {
  return Array.from(new Set(values)).sort((a, b) => a.localeCompare(b));
}

function diffArrays(current: string[], baseline: string[]) {
  const c = new Set(current);
  const b = new Set(baseline);
  return {
    added: sortedUnique(Array.from(c).filter((x) => !b.has(x))),
    removed: sortedUnique(Array.from(b).filter((x) => !c.has(x))),
  };
}

export default function AdminRightsPoliciesPage() {
  const currentAdminId = getAdminId();
  const [searchParams] = useSearchParams();
  const { currentClinicId } = useAdminClinic();
  const effectiveClinicId = currentClinicId ?? undefined;
  const { data: session, isLoading: sessionLoading } = useAdminSession();
  const canManage = (session?.permissions ?? []).includes(ADMIN_PERM_RBAC_MANAGE);
  const catalogQ = useRbacCatalog(effectiveClinicId);
  const usersQ = useRbacUsers(effectiveClinicId);
  const policiesQ = useRbacPolicies(effectiveClinicId);
  const auditQ = useRbacAudit(100, effectiveClinicId);
  const patchRolePermissions = usePatchRolePermissions();
  const patchUserRoles = usePatchUserRoles();
  const patchUserPermissions = usePatchUserPermissions();
  const patchPolicies = usePatchRbacPolicies();
  const createClinicRole = useCreateClinicRole();
  const deleteClinicRole = useDeleteClinicRole();

  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [rolePermissions, setRolePermissions] = useState<string[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [userRoleCodes, setUserRoleCodes] = useState<string[]>([]);
  const [userGrantCodes, setUserGrantCodes] = useState<string[]>([]);
  const [userDenyCodes, setUserDenyCodes] = useState<string[]>([]);
  const [permissionDomainFilter, setPermissionDomainFilter] = useState<string | null>("all");
  const [permissionSearch, setPermissionSearch] = useState("");
  /** Page UI language: Russian (default) or English for all labels and help text on this screen. */
  const [uiLocale, setUiLocale] = useState<UiLocale>("ru");
  const [glossaryOpen, setGlossaryOpen] = useState(false);
  const [criticalOpen, setCriticalOpen] = useState(false);
  const [criticalChecked, setCriticalChecked] = useState(false);
  const [criticalTitle, setCriticalTitle] = useState("");
  const [criticalMessage, setCriticalMessage] = useState("");
  const [pendingCriticalAction, setPendingCriticalAction] = useState<
    | { kind: "role"; roleId: string; permissionCodes: string[] }
    | { kind: "user_roles"; userId: string; roleCodes: string[] }
    | { kind: "user_permissions"; userId: string; overrides: { permission_code: string; effect: "grant" | "deny" }[] }
    | null
  >(null);

  const [createRoleModalOpen, setCreateRoleModalOpen] = useState(false);
  const [newRoleCode, setNewRoleCode] = useState("");
  const [newRoleName, setNewRoleName] = useState("");
  const [newRoleNote, setNewRoleNote] = useState("");
  const [createRolePerms, setCreateRolePerms] = useState<string[]>([]);
  const [createRolePreset, setCreateRolePreset] = useState<string | null>(null);
  const [createRoleCopyFromId, setCreateRoleCopyFromId] = useState<string | null>(null);
  const [createRoleError, setCreateRoleError] = useState<string | null>(null);
  const [deleteRoleOpen, setDeleteRoleOpen] = useState(false);

  const [mainTab, setMainTab] = useState<string>("roles");

  const [policyForm, setPolicyForm] = useState({
    allow_patient_disable_discount_notifications: false,
    allow_patient_disable_reminders: false,
    allow_patient_disable_all_notifications: false,
    owner_morning_brief_enabled: false,
    morning_brief_send_at_utc: "",
    owner_telegram_chat_id: "",
    ai_supervisor_enabled: false,
    ai_supervisor_send_at_utc: "",
    ai_supervisor_recipient_chat_ids: "",
  });

  const t = useMemo(() => getRbacRightsPoliciesCopy(uiLocale), [uiLocale]);

  const openCreateRoleModal = useCallback(() => {
    setCreateRoleError(null);
    setNewRoleCode("");
    setNewRoleName("");
    setNewRoleNote("");
    setCreateRolePerms([]);
    setCreateRolePreset(null);
    setCreateRoleCopyFromId(null);
    setCreateRoleModalOpen(true);
  }, []);

  const roleOptions = useMemo(
    () =>
      (catalogQ.data?.roles ?? []).map((r) => ({
        value: r.id,
        label: `${r.name} (${r.code})`,
      })),
    [catalogQ.data?.roles]
  );
  const catalogByCode = useMemo(() => {
    const m = new Map<string, RbacPermissionRead>();
    for (const p of catalogQ.data?.permissions ?? []) {
      m.set(p.code, p);
    }
    return m;
  }, [catalogQ.data?.permissions]);

  const permissionOptions = useMemo(
    () =>
      (catalogQ.data?.permissions ?? [])
        .filter((p) => (permissionDomainFilter === "all" ? true : p.domain === permissionDomainFilter))
        .filter((p) => {
          const q = permissionSearch.trim().toLowerCase();
          if (!q) return true;
          return (
            p.code.toLowerCase().includes(q) ||
            (p.description ?? "").toLowerCase().includes(q) ||
            p.domain.toLowerCase().includes(q)
          );
        })
        .map((p) => ({
          value: p.code,
          label: `${p.description ? `${p.description} · ` : ""}${p.code}`,
        })),
    [catalogQ.data?.permissions, permissionDomainFilter, permissionSearch]
  );
  const permissionDomainOptions = useMemo(() => {
    const domains = sortedUnique((catalogQ.data?.permissions ?? []).map((p) => p.domain));
    return [
      { value: "all", label: getDomainPlainSelectLabel("all", uiLocale) },
      ...domains.map((d) => ({ value: d, label: getDomainPlainSelectLabel(d, uiLocale) })),
    ];
  }, [catalogQ.data?.permissions, uiLocale]);
  const domainGlossaryRows = useMemo(() => {
    const domains = sortedUnique((catalogQ.data?.permissions ?? []).map((p) => p.domain));
    return domains.map((domain) => ({
      domain,
      glossary: getDomainGlossary(domain),
      allCodes: sortedUnique(
        (catalogQ.data?.permissions ?? [])
          .filter((p) => p.domain === domain)
          .map((p) => p.code)
      ),
    }));
  }, [catalogQ.data?.permissions]);
  const roleCodeOptions = useMemo(
    () =>
      (catalogQ.data?.roles ?? [])
        .sort((a, b) => a.code.localeCompare(b.code))
        .map((r) => ({
          value: r.code,
          label: `${r.name} (${r.code})`,
        })),
    [catalogQ.data?.roles]
  );
  const fillFromRoleOptions = useMemo(
    () =>
      (catalogQ.data?.roles ?? [])
        .filter((r) => r.code !== "owner")
        .map((r) => ({
          value: r.id,
          label: `${r.name} (${r.code})`,
        })),
    [catalogQ.data?.roles]
  );
  const createModalPermissionOptions = useMemo(
    () =>
      (catalogQ.data?.permissions ?? []).map((p) => ({
        value: p.code,
        label: `${p.description ? `${p.description} · ` : ""}${p.code}`,
      })),
    [catalogQ.data?.permissions]
  );
  const userOptions = useMemo(
    () =>
      (usersQ.data?.items ?? []).map((u) => ({
        value: u.admin_id,
        label: `${u.full_name || u.email} (${u.email})`,
      })),
    [usersQ.data?.items]
  );

  useEffect(() => {
    if (!selectedRoleId) return;
    const row = (catalogQ.data?.roles ?? []).find((r) => r.id === selectedRoleId);
    setRolePermissions(row?.permission_codes ?? []);
  }, [selectedRoleId, catalogQ.data?.roles]);

  useEffect(() => {
    if (!selectedUserId) return;
    const row = (usersQ.data?.items ?? []).find((u) => u.admin_id === selectedUserId);
    setUserRoleCodes(row?.role_codes ?? []);
    setUserGrantCodes((row?.direct_overrides ?? []).filter((x) => x.effect === "grant").map((x) => x.permission_code));
    setUserDenyCodes((row?.direct_overrides ?? []).filter((x) => x.effect === "deny").map((x) => x.permission_code));
  }, [selectedUserId, usersQ.data?.items]);

  useEffect(() => {
    const u = searchParams.get("user");
    if (!u || !usersQ.data?.items?.length) return;
    const hit = usersQ.data.items.find((x) => x.admin_id === u);
    if (hit) {
      setSelectedUserId(u);
      setMainTab("users");
    }
  }, [searchParams, usersQ.data?.items]);

  useEffect(() => {
    const p = policiesQ.data;
    if (!p) return;
    setPolicyForm({
      allow_patient_disable_discount_notifications: p.allow_patient_disable_discount_notifications,
      allow_patient_disable_reminders: p.allow_patient_disable_reminders,
      allow_patient_disable_all_notifications: p.allow_patient_disable_all_notifications,
      owner_morning_brief_enabled: p.owner_morning_brief_enabled,
      morning_brief_send_at_utc: p.morning_brief_send_at_utc ?? "",
      owner_telegram_chat_id: p.owner_telegram_chat_id ?? "",
      ai_supervisor_enabled: p.ai_supervisor_enabled,
      ai_supervisor_send_at_utc: p.ai_supervisor_send_at_utc ?? "",
      ai_supervisor_recipient_chat_ids: (p.ai_supervisor_recipient_chat_ids ?? []).join(", "),
    });
  }, [policiesQ.data]);

  const selectedRole = useMemo(
    () => (catalogQ.data?.roles ?? []).find((r) => r.id === selectedRoleId) ?? null,
    [catalogQ.data?.roles, selectedRoleId]
  );
  const roleDiff = useMemo(
    () => diffArrays(rolePermissions, selectedRole?.permission_codes ?? []),
    [rolePermissions, selectedRole?.permission_codes]
  );
  const isOwnerRoleSelected = selectedRole?.code === "owner";
  const canDeleteSelectedClinicRole = Boolean(selectedRole?.clinic_id);

  const selectedUser = useMemo(
    () => (usersQ.data?.items ?? []).find((u) => u.admin_id === selectedUserId) ?? null,
    [usersQ.data?.items, selectedUserId]
  );
  const isOwnerUserSelected = (selectedUser?.role_codes ?? []).includes("owner");
  const userRolesDiff = useMemo(
    () => diffArrays(userRoleCodes, selectedUser?.role_codes ?? []),
    [userRoleCodes, selectedUser?.role_codes]
  );
  const removedCriticalRoles = useMemo(
    () => userRolesDiff.removed.filter((x) => x === "owner" || x === "manager"),
    [userRolesDiff.removed]
  );
  const userGrantDiff = useMemo(
    () =>
      diffArrays(
        userGrantCodes,
        (selectedUser?.direct_overrides ?? [])
          .filter((x) => x.effect === "grant")
          .map((x) => x.permission_code)
      ),
    [userGrantCodes, selectedUser?.direct_overrides]
  );
  const userDenyDiff = useMemo(
    () =>
      diffArrays(
        userDenyCodes,
        (selectedUser?.direct_overrides ?? [])
          .filter((x) => x.effect === "deny")
          .map((x) => x.permission_code)
      ),
    [userDenyCodes, selectedUser?.direct_overrides]
  );
  const isEditingCurrentAdmin = selectedUserId != null && selectedUserId === currentAdminId;

  const submitCreateClinicRole = useCallback(() => {
    setCreateRoleError(null);
    const code = newRoleCode.trim().toLowerCase();
    if (!/^[a-z][a-z0-9_]*$/.test(code)) {
      setCreateRoleError(t.errCreateRoleCode);
      return;
    }
    if (!newRoleName.trim()) {
      setCreateRoleError(t.errCreateRoleName);
      return;
    }
    if (createRolePerms.length < 1) {
      setCreateRoleError(t.errCreateRolePerms);
      return;
    }
    createClinicRole.mutate(
      {
        code,
        name: newRoleName.trim(),
        permission_codes: sortedUnique(createRolePerms),
        note: newRoleNote.trim() || null,
        effectiveClinicId,
        uiLocale,
      },
      {
        onSuccess: (data) => {
          setCreateRoleModalOpen(false);
          setSelectedRoleId(data.id);
          setRolePermissions(data.permission_codes);
        },
        onError: (e: unknown) => {
          setCreateRoleError(e instanceof Error ? e.message : String(e));
        },
      }
    );
  }, [
    newRoleCode,
    newRoleName,
    newRoleNote,
    createRolePerms,
    effectiveClinicId,
    createClinicRole,
    t,
    uiLocale,
  ]);

  const policyBaseline = policiesQ.data;
  const parsedRecipientList = useMemo(
    () =>
      policyForm.ai_supervisor_recipient_chat_ids
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
    [policyForm.ai_supervisor_recipient_chat_ids]
  );
  const policyDiffRows = useMemo(() => {
    if (!policyBaseline) return [] as { key: string; before: string; after: string }[];
    const rows: { key: string; before: string; after: string }[] = [];
    const pushIfChanged = (key: string, before: string, after: string) => {
      if (before !== after) rows.push({ key, before, after });
    };
    pushIfChanged(
      "allow_patient_disable_discount_notifications",
      String(policyBaseline.allow_patient_disable_discount_notifications),
      String(policyForm.allow_patient_disable_discount_notifications)
    );
    pushIfChanged(
      "allow_patient_disable_reminders",
      String(policyBaseline.allow_patient_disable_reminders),
      String(policyForm.allow_patient_disable_reminders)
    );
    pushIfChanged(
      "allow_patient_disable_all_notifications",
      String(policyBaseline.allow_patient_disable_all_notifications),
      String(policyForm.allow_patient_disable_all_notifications)
    );
    pushIfChanged(
      "owner_morning_brief_enabled",
      String(policyBaseline.owner_morning_brief_enabled),
      String(policyForm.owner_morning_brief_enabled)
    );
    pushIfChanged(
      "morning_brief_send_at_utc",
      policyBaseline.morning_brief_send_at_utc ?? "",
      policyForm.morning_brief_send_at_utc
    );
    pushIfChanged(
      "owner_telegram_chat_id",
      policyBaseline.owner_telegram_chat_id ?? "",
      policyForm.owner_telegram_chat_id
    );
    pushIfChanged(
      "ai_supervisor_enabled",
      String(policyBaseline.ai_supervisor_enabled),
      String(policyForm.ai_supervisor_enabled)
    );
    pushIfChanged(
      "ai_supervisor_send_at_utc",
      policyBaseline.ai_supervisor_send_at_utc ?? "",
      policyForm.ai_supervisor_send_at_utc
    );
    pushIfChanged(
      "ai_supervisor_recipient_chat_ids",
      (policyBaseline.ai_supervisor_recipient_chat_ids ?? []).join(","),
      parsedRecipientList.join(",")
    );
    return rows;
  }, [policyBaseline, policyForm, parsedRecipientList]);

  const executePendingCriticalAction = () => {
    if (!pendingCriticalAction) return;
    if (pendingCriticalAction.kind === "role") {
      patchRolePermissions.mutate({
        roleId: pendingCriticalAction.roleId,
        permission_codes: pendingCriticalAction.permissionCodes,
        effectiveClinicId,
      });
    } else if (pendingCriticalAction.kind === "user_roles") {
      patchUserRoles.mutate({
        userId: pendingCriticalAction.userId,
        role_codes: pendingCriticalAction.roleCodes,
        effectiveClinicId,
      });
    } else if (pendingCriticalAction.kind === "user_permissions") {
      patchUserPermissions.mutate({
        userId: pendingCriticalAction.userId,
        overrides: pendingCriticalAction.overrides,
        effectiveClinicId,
      });
    }
    setPendingCriticalAction(null);
    setCriticalOpen(false);
    setCriticalChecked(false);
  };

  const exportDomainsCsv = useCallback(() => {
    const rows: string[][] = [
      [
        "domain_key",
        "title_ru",
        "title_en",
        "description_ru",
        "details_ru",
        "description_en",
        "details_en",
        "permission_codes_semicolon",
        "permission_count",
      ],
    ];
    for (const row of domainGlossaryRows) {
      const codes = row.allCodes;
      rows.push([
        row.domain,
        row.glossary.ruShort,
        row.glossary.enShort,
        row.glossary.ruGentle,
        row.glossary.ruInside,
        row.glossary.enGentle,
        row.glossary.enInside,
        codes.join(";"),
        String(codes.length),
      ]);
    }
    downloadUtf8Csv(
      `rbac_domain_catalog_${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.csv`,
      rows
    );
  }, [domainGlossaryRows]);

  const exportPermissionsCsv = useCallback(() => {
    const rows: string[][] = [["permission_code", "domain_key", "description"]];
    const perms = [...(catalogQ.data?.permissions ?? [])].sort((a, b) => a.code.localeCompare(b.code));
    for (const p of perms) {
      rows.push([p.code, p.domain, p.description ?? ""]);
    }
    downloadUtf8Csv(
      `rbac_permission_catalog_${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.csv`,
      rows
    );
  }, [catalogQ.data?.permissions]);

  const renderDomainOption = useCallback(
    ({ option }: { option: ComboboxItem }) => {
      const d = String(option.value ?? "");
      const g = getDomainGlossary(d);
      const primary = getDomainPrimaryLabel(d, uiLocale);
      const tip =
        uiLocale === "ru" ? (
          <Stack gap="xs">
            <Text size="sm">{g.ruGentle}</Text>
            <Text size="sm" c="dimmed">
              {g.ruInside}
            </Text>
          </Stack>
        ) : (
          <Stack gap="xs">
            <Text size="sm">{g.enGentle}</Text>
            <Text size="sm" c="dimmed">
              {g.enInside}
            </Text>
          </Stack>
        );
      return (
        <Tooltip
          label={tip}
          multiline
          styles={rbacTooltipStyles}
          position="right-start"
          withArrow
          openDelay={200}
        >
          <Box w="100%">
            <Group gap="xs" justify="space-between" wrap="nowrap">
              <Text size="sm" fw={500} style={{ flex: 1 }}>
                {primary}
              </Text>
              {d !== "all" ? (
                <Text size="xs" c="dimmed" ff="monospace">
                  {d}
                </Text>
              ) : null}
            </Group>
          </Box>
        </Tooltip>
      );
    },
    [uiLocale]
  );

  const renderPermissionOption = useCallback(
    ({ option }: { option: ComboboxItem }) => {
      const code = String(option.value ?? "");
      const p = catalogByCode.get(code);
      const desc = p?.description ?? "";
      const tip = (
        <Stack gap="xs">
          <Text size="sm" fw={600} ff="monospace">
            {code}
          </Text>
          {desc ? (
            <Text size="sm">{desc}</Text>
          ) : (
            <Text size="sm" c="dimmed">
              {t.badgeNoDescription}
            </Text>
          )}
          {t.catalogDescriptionLanguageNote ? (
            <Text size="xs" c="dimmed">
              {t.catalogDescriptionLanguageNote}
            </Text>
          ) : null}
        </Stack>
      );
      return (
        <Tooltip
          label={tip}
          multiline
          styles={rbacTooltipStyles}
          position="right-start"
          withArrow
          openDelay={200}
        >
          <Box w="100%">
            <Group gap="xs" justify="space-between" wrap="nowrap">
              <Text size="sm" lineClamp={2} style={{ flex: 1 }}>
                {desc || code}
              </Text>
              <Text size="xs" c="dimmed" ff="monospace">
                {code}
              </Text>
            </Group>
          </Box>
        </Tooltip>
      );
    },
    [catalogByCode, t]
  );

  if (sessionLoading || catalogQ.isLoading || usersQ.isLoading || policiesQ.isLoading || auditQ.isLoading) {
    return (
      <Stack gap="md">
        <ContextBar title={t.pageTitle} />
        <PageSkeleton variant="table" rows={8} />
      </Stack>
    );
  }
  if (catalogQ.isError || usersQ.isError || policiesQ.isError || auditQ.isError) {
    return (
      <Stack gap="md">
        <ContextBar title={t.pageTitle} />
        <QueryErrorAlert error={catalogQ.error || usersQ.error || policiesQ.error || auditQ.error} />
      </Stack>
    );
  }

  if (!canManage) {
    return (
      <Stack gap="md">
        <ContextBar title={t.pageTitle} />
        <Alert color="red" title={t.noAccessTitle}>
          {t.noAccessBody}
        </Alert>
      </Stack>
    );
  }

  return (
    <Stack gap="lg">
      <ContextBar title={t.pageTitle} />
      <Text size="md" c="dimmed" maw={900}>
        {t.intro}
      </Text>
      <Paper withBorder p="md" radius="md" shadow="xs">
        <Group justify="space-between" align="center" wrap="wrap" gap="sm">
          <Text size="sm" fw={600}>
            {t.languageLabel}
          </Text>
          <SegmentedControl
            size="sm"
            value={uiLocale}
            onChange={(v) => setUiLocale(v as UiLocale)}
            data={[
              { value: "ru", label: t.langRu },
              { value: "en", label: t.langEn },
            ]}
          />
        </Group>
      </Paper>

      <Stack gap="md">
        <Paper
          radius="md"
          p="lg"
          shadow="sm"
          withBorder
          style={{ borderLeft: "4px solid var(--mantine-color-teal-6)" }}
        >
          <Group align="flex-start" gap="md" wrap="nowrap">
            <ThemeIcon size={48} radius="md" variant="light" color="teal">
              <IconInfoCircle size={26} stroke={1.5} />
            </ThemeIcon>
            <Stack gap="sm" style={{ flex: 1 }}>
              <Text fw={700} size="lg">
                {t.domainHelpTitle}
              </Text>
              <Text size="sm">{t.domainHelpP1}</Text>
              <Text size="sm">{t.domainHelpP2}</Text>
              <Text size="sm" c="dimmed">
                {t.domainHelpP3}
              </Text>
            </Stack>
          </Group>
        </Paper>

        <Paper
          radius="md"
          p="lg"
          shadow="sm"
          withBorder
          style={{ borderLeft: "4px solid var(--mantine-color-blue-6)" }}
        >
          <Group align="flex-start" gap="md" wrap="nowrap">
            <ThemeIcon size={48} radius="md" variant="light" color="blue">
              <IconShieldCheck size={26} stroke={1.5} />
            </ThemeIcon>
            <Stack gap="sm" style={{ flex: 1 }}>
              <Text fw={700} size="lg">
                {t.safeTitle}
              </Text>
              <Text size="sm">{t.safeStep1}</Text>
              <Text size="sm">{t.safeStep2}</Text>
              <Text size="sm">{t.safeStep3}</Text>
            </Stack>
          </Group>
        </Paper>

        <Paper
          radius="md"
          p="lg"
          shadow="sm"
          withBorder
          bg="gray.0"
          style={{ borderLeft: "4px solid var(--mantine-color-gray-6)" }}
        >
          <Group align="flex-start" gap="md" wrap="nowrap">
            <ThemeIcon size={48} radius="md" variant="light" color="gray">
              <IconBook size={26} stroke={1.5} />
            </ThemeIcon>
            <Stack gap="sm" style={{ flex: 1 }}>
              <Text fw={700} size="lg">
                {t.glossaryTitle}
              </Text>
              <Text size="sm">{t.glossaryRole}</Text>
              <Text size="sm">{t.glossaryPermission}</Text>
              <Text size="sm">{t.glossaryGrant}</Text>
              <Text size="sm">{t.glossaryDeny}</Text>
              <Text size="sm">{t.glossaryDomain}</Text>
            </Stack>
          </Group>
        </Paper>
      </Stack>

      <Tabs value={mainTab} onChange={(v) => setMainTab(v ?? "roles")}>
        <Tabs.List>
          <Tabs.Tab value="roles">{t.tabRoles}</Tabs.Tab>
          <Tabs.Tab value="users">{t.tabUsers}</Tabs.Tab>
          <Tabs.Tab value="policies">{t.tabPolicies}</Tabs.Tab>
          <Tabs.Tab value="audit">{t.tabAudit}</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="roles" pt="md">
          <Card withBorder>
            <Stack gap="sm">
              <Alert color="indigo" title={t.rolesPanelTitle}>
                {t.rolesPanelBody}
              </Alert>
              <Paper
                withBorder
                p="md"
                radius="md"
                style={{
                  borderColor: "var(--mantine-color-indigo-3)",
                  background: "var(--mantine-color-indigo-0)",
                }}
              >
                <Group justify="space-between" align="flex-start" wrap="wrap" gap="md">
                  <Stack gap={6} maw={560} style={{ flex: "1 1 240px" }}>
                    <Text fw={600} size="sm">
                      {t.rolesPanelCreateBlockTitle}
                    </Text>
                    <Text size="sm" c="dimmed">
                      {t.rolesPanelCreateBlockHint}
                    </Text>
                  </Stack>
                  <Button
                    leftSection={<IconPlus size={18} />}
                    size="sm"
                    variant="filled"
                    color="indigo"
                    onClick={openCreateRoleModal}
                  >
                    {t.btnCreateClinicRole}
                  </Button>
                </Group>
              </Paper>
              <Stack gap={6}>
                <Text size="sm" fw={500}>
                  {t.labelRole}
                </Text>
                <Select
                  placeholder={t.phRole}
                  value={selectedRoleId}
                  onChange={setSelectedRoleId}
                  data={roleOptions}
                  searchable
                />
              </Stack>
              <Group grow>
                <Select
                  label={t.labelDomain}
                  value={permissionDomainFilter}
                  onChange={setPermissionDomainFilter}
                  data={permissionDomainOptions}
                  searchable
                  renderOption={renderDomainOption}
                  maxDropdownHeight={320}
                />
                <TextInput
                  label={t.labelSearch}
                  placeholder={t.phSearchRoles}
                  value={permissionSearch}
                  onChange={(e) => setPermissionSearch(e.currentTarget.value)}
                />
              </Group>
              <Text size="xs" c="dimmed">
                {t.tipDomainFilter}
              </Text>
              <MultiSelect
                label={t.labelRolePermissions}
                value={rolePermissions}
                onChange={setRolePermissions}
                data={permissionOptions}
                searchable
                disabled={isOwnerRoleSelected}
                renderOption={renderPermissionOption}
                maxDropdownHeight={360}
              />
              {isOwnerRoleSelected ? (
                <Alert color="yellow" title={t.ownerRoleProtectedTitle}>
                  {t.ownerRoleProtectedBody}
                </Alert>
              ) : null}
              {selectedRoleId ? (
                <Card withBorder bg="gray.0">
                  <Stack gap={6}>
                    <Text size="xs" c="dimmed">
                      {t.diffRole}
                    </Text>
                    <Group gap={6}>
                      {roleDiff.added.map((c) => (
                        <Tooltip
                          key={`add-${c}`}
                          label={catalogByCode.get(c)?.description ?? t.badgeNoDescription}
                          multiline
                          maw={320}
                          withArrow
                          styles={rbacTooltipStyles}
                        >
                          <Badge color="green" variant="light">
                            + {c}
                          </Badge>
                        </Tooltip>
                      ))}
                      {roleDiff.removed.map((c) => (
                        <Tooltip
                          key={`del-${c}`}
                          label={catalogByCode.get(c)?.description ?? t.badgeNoDescription}
                          multiline
                          maw={320}
                          withArrow
                          styles={rbacTooltipStyles}
                        >
                          <Badge color="red" variant="light">
                            - {c}
                          </Badge>
                        </Tooltip>
                      ))}
                      {roleDiff.added.length === 0 && roleDiff.removed.length === 0 ? (
                        <Text size="xs" c="dimmed">
                          {t.noChanges}
                        </Text>
                      ) : null}
                    </Group>
                  </Stack>
                </Card>
              ) : null}
              <Group justify="flex-end" gap="sm">
                {canDeleteSelectedClinicRole ? (
                  <Button
                    color="red"
                    variant="light"
                    onClick={() => setDeleteRoleOpen(true)}
                    disabled={!selectedRoleId || patchRolePermissions.isPending}
                  >
                    {t.btnDeleteClinicRole}
                  </Button>
                ) : null}
                <Button
                  onClick={() => {
                    if (!selectedRoleId) return;
                    const isCritical =
                      isOwnerRoleSelected &&
                      (roleDiff.added.length > 0 || roleDiff.removed.length > 0);
                    if (isCritical) {
                      setCriticalTitle(t.criticalOwnerRole);
                      setCriticalMessage(t.criticalOwnerRoleMsg);
                      setPendingCriticalAction({
                        kind: "role",
                        roleId: selectedRoleId,
                        permissionCodes: rolePermissions,
                      });
                      setCriticalChecked(false);
                      setCriticalOpen(true);
                      return;
                    }
                    patchRolePermissions.mutate({
                      roleId: selectedRoleId,
                      permission_codes: rolePermissions,
                      effectiveClinicId,
                    });
                  }}
                  loading={patchRolePermissions.isPending}
                  disabled={!selectedRoleId || isOwnerRoleSelected}
                >
                  {t.saveRolePermissions}
                </Button>
              </Group>
            </Stack>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="users" pt="md">
          <Card withBorder>
            <Stack gap="sm">
              <Alert color="indigo" title={t.usersPanelTitle}>
                {t.usersPanelBody}
              </Alert>
              <Select
                label={t.labelEmployee}
                placeholder={t.phEmployee}
                value={selectedUserId}
                onChange={setSelectedUserId}
                data={userOptions}
                searchable
              />
              <Group grow>
                <Select
                  label={t.labelDomain}
                  value={permissionDomainFilter}
                  onChange={setPermissionDomainFilter}
                  data={permissionDomainOptions}
                  searchable
                  renderOption={renderDomainOption}
                  maxDropdownHeight={320}
                />
                <TextInput
                  label={t.labelSearch}
                  placeholder={t.phSearchUsers}
                  value={permissionSearch}
                  onChange={(e) => setPermissionSearch(e.currentTarget.value)}
                />
              </Group>
              <MultiSelect
                label={t.labelUserRoles}
                value={userRoleCodes}
                onChange={setUserRoleCodes}
                data={roleCodeOptions}
                disabled={isOwnerUserSelected}
              />
              {isOwnerUserSelected ? (
                <Alert color="yellow" title={t.ownerUserProtectedTitle}>
                  {t.ownerUserProtectedBody}
                </Alert>
              ) : null}
              {selectedUserId ? (
                <Card withBorder bg="gray.0">
                  <Stack gap={6}>
                    <Text size="xs" c="dimmed">
                      {t.diffUserRoles}
                    </Text>
                    <Group gap={6}>
                      {userRolesDiff.added.map((c) => (
                        <Tooltip
                          key={`ura-${c}`}
                          label={`${t.roleCodeTooltip}: ${c}`}
                          withArrow
                          styles={rbacTooltipStyles}
                        >
                          <Badge color="green" variant="light">
                            + {c}
                          </Badge>
                        </Tooltip>
                      ))}
                      {userRolesDiff.removed.map((c) => (
                        <Tooltip
                          key={`urr-${c}`}
                          label={`${t.roleCodeTooltip}: ${c}`}
                          withArrow
                          styles={rbacTooltipStyles}
                        >
                          <Badge color="red" variant="light">
                            - {c}
                          </Badge>
                        </Tooltip>
                      ))}
                      {userRolesDiff.added.length === 0 && userRolesDiff.removed.length === 0 ? (
                        <Text size="xs" c="dimmed">
                          {t.noChanges}
                        </Text>
                      ) : null}
                    </Group>
                  </Stack>
                </Card>
              ) : null}
              <Group justify="flex-end">
                <Button
                  variant="light"
                  onClick={() => {
                    if (!selectedUserId) return;
                    const removingOwnCriticalRole =
                      isEditingCurrentAdmin && removedCriticalRoles.length > 0;
                    if (removingOwnCriticalRole) {
                      setCriticalTitle(t.criticalSelfRole);
                      setCriticalMessage(
                        t.criticalSelfRoleMsg.replace("{roles}", removedCriticalRoles.join(", "))
                      );
                      setPendingCriticalAction({
                        kind: "user_roles",
                        userId: selectedUserId,
                        roleCodes: userRoleCodes,
                      });
                      setCriticalChecked(false);
                      setCriticalOpen(true);
                      return;
                    }
                    patchUserRoles.mutate({
                      userId: selectedUserId,
                      role_codes: userRoleCodes,
                      effectiveClinicId,
                    });
                  }}
                  loading={patchUserRoles.isPending}
                  disabled={!selectedUserId || isOwnerUserSelected}
                >
                  {t.saveUserRoles}
                </Button>
              </Group>
              <MultiSelect
                label={t.labelGrant}
                value={userGrantCodes}
                onChange={setUserGrantCodes}
                data={permissionOptions}
                searchable
                disabled={isOwnerUserSelected}
                renderOption={renderPermissionOption}
                maxDropdownHeight={360}
              />
              <MultiSelect
                label={t.labelDeny}
                value={userDenyCodes}
                onChange={setUserDenyCodes}
                data={permissionOptions}
                searchable
                disabled={isOwnerUserSelected}
                renderOption={renderPermissionOption}
                maxDropdownHeight={360}
              />
              {isOwnerUserSelected ? (
                <Alert color="yellow" title={t.ownerOverridesTitle}>
                  {t.ownerOverridesBody}
                </Alert>
              ) : null}
              <Card withBorder bg="gray.0">
                <Stack gap={4}>
                  <Text fw={600} size="xs">
                    {t.grantDenyGuideTitle}
                  </Text>
                  <Text size="xs">
                    {t.grantDenyGuide1}
                  </Text>
                  <Text size="xs">
                    {t.grantDenyGuide2}
                  </Text>
                  <Text size="xs">
                    {t.grantDenyGuide3}
                  </Text>
                </Stack>
              </Card>
              {selectedUserId ? (
                <Card withBorder bg="gray.0">
                  <Stack gap={6}>
                    <Text size="xs" c="dimmed">
                      {t.diffGrant}
                    </Text>
                    <Group gap={6}>
                      {userGrantDiff.added.map((c) => (
                        <Tooltip
                          key={`uga-${c}`}
                          label={catalogByCode.get(c)?.description ?? t.badgeNoDescription}
                          multiline
                          maw={320}
                          withArrow
                          styles={rbacTooltipStyles}
                        >
                          <Badge color="green" variant="light">
                            + {c}
                          </Badge>
                        </Tooltip>
                      ))}
                      {userGrantDiff.removed.map((c) => (
                        <Tooltip
                          key={`ugr-${c}`}
                          label={catalogByCode.get(c)?.description ?? t.badgeNoDescription}
                          multiline
                          maw={320}
                          withArrow
                          styles={rbacTooltipStyles}
                        >
                          <Badge color="red" variant="light">
                            - {c}
                          </Badge>
                        </Tooltip>
                      ))}
                      {userGrantDiff.added.length === 0 && userGrantDiff.removed.length === 0 ? (
                        <Text size="xs" c="dimmed">
                          {t.noChanges}
                        </Text>
                      ) : null}
                    </Group>
                    <Divider />
                    <Text size="xs" c="dimmed">
                      {t.diffDeny}
                    </Text>
                    <Group gap={6}>
                      {userDenyDiff.added.map((c) => (
                        <Tooltip
                          key={`uda-${c}`}
                          label={catalogByCode.get(c)?.description ?? t.badgeNoDescription}
                          multiline
                          maw={320}
                          withArrow
                          styles={rbacTooltipStyles}
                        >
                          <Badge color="green" variant="light">
                            + {c}
                          </Badge>
                        </Tooltip>
                      ))}
                      {userDenyDiff.removed.map((c) => (
                        <Tooltip
                          key={`udr-${c}`}
                          label={catalogByCode.get(c)?.description ?? t.badgeNoDescription}
                          multiline
                          maw={320}
                          withArrow
                          styles={rbacTooltipStyles}
                        >
                          <Badge color="red" variant="light">
                            - {c}
                          </Badge>
                        </Tooltip>
                      ))}
                      {userDenyDiff.added.length === 0 && userDenyDiff.removed.length === 0 ? (
                        <Text size="xs" c="dimmed">
                          {t.noChanges}
                        </Text>
                      ) : null}
                    </Group>
                  </Stack>
                </Card>
              ) : null}
              <Group justify="flex-end">
                <Button
                  onClick={() => {
                    if (!selectedUserId) return;
                    const overrides = [
                      ...userGrantCodes.map((permission_code) => ({ permission_code, effect: "grant" as const })),
                      ...userDenyCodes.map((permission_code) => ({ permission_code, effect: "deny" as const })),
                    ];
                    const denySelfRbacManage =
                      isEditingCurrentAdmin &&
                      overrides.some(
                        (x) => x.permission_code === ADMIN_PERM_RBAC_MANAGE && x.effect === "deny"
                      );
                    if (denySelfRbacManage) {
                      setCriticalTitle(t.criticalSelfRbac);
                      setCriticalMessage(t.criticalSelfRbacMsg);
                      setPendingCriticalAction({
                        kind: "user_permissions",
                        userId: selectedUserId,
                        overrides,
                      });
                      setCriticalChecked(false);
                      setCriticalOpen(true);
                      return;
                    }
                    patchUserPermissions.mutate({
                      userId: selectedUserId,
                      overrides,
                      effectiveClinicId,
                    });
                  }}
                  loading={patchUserPermissions.isPending}
                  disabled={!selectedUserId || isOwnerUserSelected}
                >
                  {t.saveUserPermissions}
                </Button>
              </Group>
              {selectedUserId ? (
                <Card withBorder bg="gray.0">
                  <Stack gap={4}>
                    <Text size="xs" c="dimmed">
                      {t.effectivePermissions}
                    </Text>
                    <Group gap={6}>
                      {((usersQ.data?.items ?? []).find((u) => u.admin_id === selectedUserId)?.effective_permission_codes ?? []).map((c) => (
                        <Tooltip
                          key={c}
                          label={catalogByCode.get(c)?.description ?? t.badgeNoDescription}
                          multiline
                          maw={300}
                          withArrow
                          styles={rbacTooltipStyles}
                        >
                          <Badge size="xs" variant="light">
                            {c}
                          </Badge>
                        </Tooltip>
                      ))}
                    </Group>
                  </Stack>
                </Card>
              ) : null}
            </Stack>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="policies" pt="md">
          <Card withBorder>
            <Stack gap="sm">
              <Alert color="indigo" title={t.policiesPanelTitle}>
                {t.policiesPanelBody}
              </Alert>
              <Switch
                label={t.swDiscount}
                checked={policyForm.allow_patient_disable_discount_notifications}
                onChange={(e) =>
                  setPolicyForm((p) => ({ ...p, allow_patient_disable_discount_notifications: e.currentTarget.checked }))
                }
              />
              <Switch
                label={t.swReminders}
                checked={policyForm.allow_patient_disable_reminders}
                onChange={(e) =>
                  setPolicyForm((p) => ({ ...p, allow_patient_disable_reminders: e.currentTarget.checked }))
                }
              />
              <Switch
                label={t.swAllNotif}
                checked={policyForm.allow_patient_disable_all_notifications}
                onChange={(e) =>
                  setPolicyForm((p) => ({ ...p, allow_patient_disable_all_notifications: e.currentTarget.checked }))
                }
              />
              <Switch
                label={t.swMorningBrief}
                checked={policyForm.owner_morning_brief_enabled}
                onChange={(e) =>
                  setPolicyForm((p) => ({ ...p, owner_morning_brief_enabled: e.currentTarget.checked }))
                }
              />
              <TextInput
                label={t.labelMorningBriefTime}
                value={policyForm.morning_brief_send_at_utc}
                onChange={(e) => setPolicyForm((p) => ({ ...p, morning_brief_send_at_utc: e.currentTarget.value }))}
              />
              <TextInput
                label={t.labelOwnerTg}
                value={policyForm.owner_telegram_chat_id}
                onChange={(e) => setPolicyForm((p) => ({ ...p, owner_telegram_chat_id: e.currentTarget.value }))}
              />
              <Switch
                label={t.swAiSupervisor}
                checked={policyForm.ai_supervisor_enabled}
                onChange={(e) =>
                  setPolicyForm((p) => ({ ...p, ai_supervisor_enabled: e.currentTarget.checked }))
                }
              />
              <TextInput
                label={t.labelAiSupervisorTime}
                value={policyForm.ai_supervisor_send_at_utc}
                onChange={(e) => setPolicyForm((p) => ({ ...p, ai_supervisor_send_at_utc: e.currentTarget.value }))}
              />
              <TextInput
                label={t.labelAiSupervisorRecipients}
                value={policyForm.ai_supervisor_recipient_chat_ids}
                onChange={(e) =>
                  setPolicyForm((p) => ({ ...p, ai_supervisor_recipient_chat_ids: e.currentTarget.value }))
                }
              />
              <Card withBorder bg="gray.0">
                <Stack gap={6}>
                  <Text size="xs" c="dimmed">
                    {t.diffPolicies}
                  </Text>
                  {policyDiffRows.length === 0 ? (
                    <Text size="xs" c="dimmed">
                      {t.noChanges}
                    </Text>
                  ) : (
                    <Table withTableBorder withRowBorders>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>{t.tableField}</Table.Th>
                          <Table.Th>{t.tableBefore}</Table.Th>
                          <Table.Th>{t.tableAfter}</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {policyDiffRows.map((r) => (
                          <Table.Tr key={r.key}>
                            <Table.Td>{getPolicyFieldLabel(r.key, uiLocale)}</Table.Td>
                            <Table.Td>{r.before || "—"}</Table.Td>
                            <Table.Td>{r.after || "—"}</Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  )}
                </Stack>
              </Card>
              <Group justify="flex-end">
                <Button
                  onClick={() => {
                    patchPolicies.mutate({
                      allow_patient_disable_discount_notifications:
                        policyForm.allow_patient_disable_discount_notifications,
                      allow_patient_disable_reminders: policyForm.allow_patient_disable_reminders,
                      allow_patient_disable_all_notifications:
                        policyForm.allow_patient_disable_all_notifications,
                      owner_morning_brief_enabled: policyForm.owner_morning_brief_enabled,
                      morning_brief_send_at_utc: policyForm.morning_brief_send_at_utc || null,
                      owner_telegram_chat_id: policyForm.owner_telegram_chat_id || null,
                      ai_supervisor_enabled: policyForm.ai_supervisor_enabled,
                      ai_supervisor_send_at_utc: policyForm.ai_supervisor_send_at_utc || null,
                      ai_supervisor_recipient_chat_ids: parsedRecipientList,
                      effectiveClinicId,
                    });
                  }}
                  loading={patchPolicies.isPending}
                >
                  {t.savePolicies}
                </Button>
              </Group>
            </Stack>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="audit" pt="md">
          <Card withBorder>
            <Stack gap="sm">
              <Alert color="indigo" title={t.auditPanelTitle}>
                {t.auditPanelBody}
              </Alert>
              <Table withRowBorders withTableBorder striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t.auditWhen}</Table.Th>
                  <Table.Th>{t.auditWho}</Table.Th>
                  <Table.Th>{t.auditAction}</Table.Th>
                  <Table.Th>{t.auditEntity}</Table.Th>
                  <Table.Th>{t.auditNote}</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(auditQ.data ?? []).map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>{new Date(r.created_at).toLocaleString()}</Table.Td>
                    <Table.Td>{r.actor_admin_name || r.actor_admin_id || "—"}</Table.Td>
                    <Table.Td>{r.action}</Table.Td>
                    <Table.Td>{r.entity_type}:{r.entity_id}</Table.Td>
                    <Table.Td>{r.note || "—"}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
              </Table>
            </Stack>
          </Card>
        </Tabs.Panel>
      </Tabs>
      <Card withBorder bg="gray.0">
        <Stack gap="sm">
          <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
            <Stack gap={4} style={{ flex: 1, minWidth: 240 }}>
              <Text fw={600} size="sm">
                {t.glossarySectionTitle}
              </Text>
              <Text size="xs" c="dimmed">
                {t.glossarySectionSubtitle}
              </Text>
            </Stack>
            <Group gap="xs">
              <Button size="xs" variant="light" onClick={exportDomainsCsv}>
                {t.csvDomains}
              </Button>
              <Button size="xs" variant="light" onClick={exportPermissionsCsv}>
                {t.csvPermissions}
              </Button>
            </Group>
          </Group>
          <Button variant="default" onClick={() => setGlossaryOpen((o) => !o)}>
            {glossaryOpen ? t.glossaryToggleHide : t.glossaryToggleShow}
          </Button>
          <Collapse in={glossaryOpen}>
            {domainGlossaryRows.length === 0 ? (
              <Text size="xs" c="dimmed">
                {t.glossaryEmpty}
              </Text>
            ) : (
              <Table withTableBorder withRowBorders verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>{t.thReadName}</Table.Th>
                    <Table.Th>{t.thExplanation}</Table.Th>
                    <Table.Th maw={280}>{t.thAllCodes}</Table.Th>
                    <Table.Th style={{ width: 120 }}>{t.thSystemKey}</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {domainGlossaryRows.map((row) => (
                    <Table.Tr key={row.domain}>
                      <Table.Td maw={220}>
                        <Text size="sm" fw={500}>
                          {uiLocale === "ru" ? row.glossary.ruShort : row.glossary.enShort}
                        </Text>
                      </Table.Td>
                      <Table.Td maw={360}>
                        {uiLocale === "ru" ? (
                          <>
                            <Text size="xs">{row.glossary.ruGentle}</Text>
                            <Text size="xs" mt={6} c="dimmed">
                              {row.glossary.ruInside}
                            </Text>
                          </>
                        ) : (
                          <>
                            <Text size="xs">{row.glossary.enGentle}</Text>
                            <Text size="xs" mt={6} c="dimmed">
                              {row.glossary.enInside}
                            </Text>
                          </>
                        )}
                      </Table.Td>
                      <Table.Td maw={280}>
                        <ScrollArea h={140} type="auto">
                          <Text size="xs" ff="monospace" style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                            {row.allCodes.join(", ")}
                          </Text>
                        </ScrollArea>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c="dimmed" ff="monospace">
                          {row.domain}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Collapse>
        </Stack>
      </Card>
      <Modal
        opened={createRoleModalOpen}
        onClose={() => {
          setCreateRoleModalOpen(false);
          setCreateRoleError(null);
        }}
        title={t.modalCreateRoleTitle}
        centered
        size="lg"
      >
        <Stack gap="sm">
          {createRoleError ? (
            <Alert color="red" variant="light">
              {createRoleError}
            </Alert>
          ) : null}
          <TextInput
            label={t.labelNewRoleCode}
            placeholder={t.phNewRoleCode}
            value={newRoleCode}
            onChange={(e) => setNewRoleCode(e.currentTarget.value)}
            autoComplete="off"
          />
          <TextInput
            label={t.labelNewRoleName}
            placeholder={t.phNewRoleName}
            value={newRoleName}
            onChange={(e) => setNewRoleName(e.currentTarget.value)}
            autoComplete="off"
          />
          <Select
            label={t.labelPermissionPreset}
            value={createRolePreset ?? ""}
            onChange={(v) => {
              const next = v || null;
              setCreateRolePreset(next);
              setCreateRoleCopyFromId(null);
              if (!next) return;
              const preset = (catalogQ.data?.role_presets ?? []).find((p) => p.code === next);
              if (preset) setCreateRolePerms([...preset.permission_codes]);
            }}
            data={[
              { value: "", label: t.optPresetNone },
              ...(catalogQ.data?.role_presets ?? []).map((p) => ({
                value: p.code,
                label: getRolePresetOptionLabel(p.code, t),
              })),
            ]}
            searchable
          />
          <Select
            label={t.labelFillFromRole}
            value={createRoleCopyFromId ?? ""}
            onChange={(v) => {
              const next = v || null;
              setCreateRoleCopyFromId(next);
              setCreateRolePreset(null);
              if (!next) return;
              const role = (catalogQ.data?.roles ?? []).find((r) => r.id === next);
              if (role) setCreateRolePerms([...role.permission_codes]);
            }}
            data={[{ value: "", label: t.optFillFromRoleNone }, ...fillFromRoleOptions]}
            searchable
          />
          <Text size="xs" c="dimmed">
            {t.hintCreateRolePermissions}
          </Text>
          <MultiSelect
            label={t.labelRolePermissions}
            value={createRolePerms}
            onChange={setCreateRolePerms}
            data={createModalPermissionOptions}
            searchable
            renderOption={renderPermissionOption}
            maxDropdownHeight={360}
          />
          <TextInput
            label={t.labelCreateRoleNote}
            placeholder={t.phCreateRoleNote}
            value={newRoleNote}
            onChange={(e) => setNewRoleNote(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={() => {
                setCreateRoleModalOpen(false);
                setCreateRoleError(null);
              }}
            >
              {t.cancel}
            </Button>
            <Button loading={createClinicRole.isPending} onClick={submitCreateClinicRole}>
              {t.btnSubmitNewRole}
            </Button>
          </Group>
        </Stack>
      </Modal>
      <Modal
        opened={deleteRoleOpen}
        onClose={() => setDeleteRoleOpen(false)}
        title={t.modalDeleteRoleTitle}
        centered
      >
        <Stack gap="sm">
          <Text size="sm">{t.modalDeleteRoleBody}</Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeleteRoleOpen(false)}>
              {t.cancel}
            </Button>
            <Button
              color="red"
              loading={deleteClinicRole.isPending}
              onClick={() => {
                if (!selectedRoleId) return;
                deleteClinicRole.mutate(
                  {
                    roleId: selectedRoleId,
                    effectiveClinicId,
                    uiLocale,
                  },
                  {
                    onSuccess: () => {
                      setDeleteRoleOpen(false);
                      setSelectedRoleId(null);
                      setRolePermissions([]);
                    },
                  }
                );
              }}
            >
              {t.confirmDeleteRole}
            </Button>
          </Group>
        </Stack>
      </Modal>
      <Modal
        opened={criticalOpen}
        onClose={() => {
          setCriticalOpen(false);
          setCriticalChecked(false);
          setPendingCriticalAction(null);
        }}
        title={criticalTitle || t.modalConfirm}
        centered
      >
        <Stack gap="sm">
          <Text size="sm">{criticalMessage}</Text>
          <Checkbox
            checked={criticalChecked}
            onChange={(e) => setCriticalChecked(e.currentTarget.checked)}
            label={t.modalCriticalLabel}
          />
          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={() => {
                setCriticalOpen(false);
                setCriticalChecked(false);
                setPendingCriticalAction(null);
              }}
            >
              {t.cancel}
            </Button>
            <Button color="red" disabled={!criticalChecked} onClick={executePendingCriticalAction}>
              {t.apply}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}

