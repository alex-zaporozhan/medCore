import {
  useCreateStaffDirectoryAdminMutation,
  useCreateStaffProfessionCategoryMutation,
  useDeleteStaffProfessionCategoryMutation,
  usePatchStaffDirectoryAdminMutation,
  usePatchStaffProfessionCategoryMutation,
  useRbacCatalog,
  useStaffDirectoryAdmins,
  useStaffProfessionCategories,
} from "@/hooks";
import type { StaffDirectoryAdminRow, StaffProfessionCategoryRow } from "@/hooks/useStaffDirectory";
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Divider,
  Group,
  Loader,
  Menu,
  Modal,
  MultiSelect,
  NumberInput,
  Paper,
  Progress,
  ScrollArea,
  Select,
  SimpleGrid,
  Stack,
  Stepper,
  Table,
  Tabs,
  Text,
  TextInput,
  ThemeIcon,
  Title,
  Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconBriefcase,
  IconDotsVertical,
  IconExternalLink,
  IconPencil,
  IconUsersPlus,
} from "@tabler/icons-react";
import { getAdminId } from "@/api/client";
import { ContextBar } from "@/shared/ui/ContextBar";
import { PageSkeleton } from "@/shared/ui/PageSkeleton";
import { QueryErrorAlert } from "@/shared/ui";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { ROUTE_PATHS } from "@/routePaths";
import { Link } from "react-router-dom";
import { useMemo, useState } from "react";

const MIN_PASSWORD_LENGTH = 8;

/** Подсказка ролей из каталога клиники (бэкенд требует ≥1 роли). */
function pickDefaultRoleCodes(roles: { code: string }[] | undefined): string[] {
  const codes = (roles ?? []).map((r) => r.code);
  if (codes.includes("admin")) return ["admin"];
  if (codes.includes("manager")) return ["manager"];
  if (codes.length) return [codes[0]];
  return [];
}

function humanizeStaffDirectoryError(e: unknown): string {
  const raw = e instanceof Error ? e.message : String(e);
  if (/default_role_codes/i.test(raw) || raw.includes("default_role_codes")) {
    return "Для категории нужны типовые роли: откройте «Создать категорию» и пройдите шаг «Типовые роли», либо отредактируйте категорию (карандаш).";
  }
  if (/role_codes/i.test(raw) || raw.includes("role_codes")) {
    return "Для сотрудника нужны роли: в мастере добавления сотрудника обязательно заполните шаг «Роли учётной записи».";
  }
  return raw;
}

const TAB_ALL = "all";
const TAB_NONE = "__none__";

function tabValueForCategory(categoryId: string): string {
  return `cat:${categoryId}`;
}

function parseCategoryTab(tab: string): string | null {
  if (tab === TAB_ALL || tab === TAB_NONE) return null;
  if (tab.startsWith("cat:")) return tab.slice(4);
  return null;
}

export default function AdminAdministratorsPage() {
  const { currentClinicId, selectableClinics, clinics, setCurrentClinicId } = useAdminClinic();
  const clinicId = currentClinicId;
  const clinicOptions = useMemo(
    () =>
      (selectableClinics.length ? selectableClinics : clinics).map((c) => ({
        value: c.id,
        label: c.name,
      })),
    [selectableClinics, clinics]
  );

  const { data: categories, isLoading: catLoading, isError: catError, error: catErr } =
    useStaffProfessionCategories(clinicId);
  const { data: staff, isLoading: staffLoading, isError: staffError, error: staffErr } =
    useStaffDirectoryAdmins(clinicId);

  const [staffTab, setStaffTab] = useState<string>(TAB_ALL);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [employmentError, setEmploymentError] = useState<string | null>(null);
  const [categoryEdit, setCategoryEdit] = useState<StaffDirectoryAdminRow | null>(null);
  const [categoryDraft, setCategoryDraft] = useState<string | null>(null);
  const [expandModalTab, setExpandModalTab] = useState<string | null>(null);
  const [expandOpened, { open: openExpand, close: closeExpand }] = useDisclosure(false);

  const [categoryWizardOpen, { open: openCategoryWizard, close: closeCategoryWizard }] = useDisclosure(false);
  const [categoryWizardStep, setCategoryWizardStep] = useState(0);
  const [cwName, setCwName] = useState("");
  const [cwSortOrder, setCwSortOrder] = useState(0);
  const [cwRoleCodes, setCwRoleCodes] = useState<string[]>([]);

  const [staffWizardOpen, { open: openStaffWizard, close: closeStaffWizard }] = useDisclosure(false);
  const [staffWizardStep, setStaffWizardStep] = useState(0);
  const [swEmail, setSwEmail] = useState("");
  const [swPassword, setSwPassword] = useState("");
  const [swFullName, setSwFullName] = useState("");
  const [swBirthDate, setSwBirthDate] = useState("");
  const [swProfessionCategoryId, setSwProfessionCategoryId] = useState<string | null>(null);
  const [swRoleCodes, setSwRoleCodes] = useState<string[]>([]);

  const [editCategoryRow, setEditCategoryRow] = useState<StaffProfessionCategoryRow | null>(null);
  const [ecName, setEcName] = useState("");
  const [ecSortOrder, setEcSortOrder] = useState(0);
  const [ecRoleCodes, setEcRoleCodes] = useState<string[]>([]);

  const createMut = useCreateStaffDirectoryAdminMutation(clinicId);
  const createCat = useCreateStaffProfessionCategoryMutation(clinicId);
  const patchCat = usePatchStaffProfessionCategoryMutation(clinicId);
  const deleteCat = useDeleteStaffProfessionCategoryMutation(clinicId);
  const patchStaff = usePatchStaffDirectoryAdminMutation(clinicId);
  const currentAdminId = getAdminId();

  const { data: rbacCatalog, isError: rbacCatalogError, error: rbacCatalogErr } = useRbacCatalog(clinicId);
  const roleCatalogOptions = useMemo(
    () =>
      (rbacCatalog?.roles ?? []).map((r) => ({
        value: r.code,
        label: `${r.name} (${r.code})`,
      })),
    [rbacCatalog?.roles]
  );

  const categorySelectData = useMemo(
    () =>
      (categories ?? []).map((c) => ({
        value: c.id,
        label: c.name,
      })),
    [categories]
  );

  const list = staff ?? [];
  const loading = catLoading || staffLoading;

  const filteredForTab = (tab: string) => {
    if (tab === TAB_ALL) return list;
    if (tab === TAB_NONE) return list.filter((a) => !a.profession_category_id);
    const cid = parseCategoryTab(tab);
    if (!cid) return list;
    return list.filter((a) => a.profession_category_id === cid);
  };

  const counts = useMemo(() => {
    const none = list.filter((a) => !a.profession_category_id).length;
    const byCat: Record<string, number> = {};
    for (const c of categories ?? []) {
      byCat[c.id] = list.filter((a) => a.profession_category_id === c.id).length;
    }
    return { none, byCat, all: list.length };
  }, [list, categories]);

  const resetCategoryWizard = () => {
    setCategoryWizardStep(0);
    setCwName("");
    setCwSortOrder((categories ?? []).length);
    setCwRoleCodes([]);
  };

  const handleOpenCategoryWizard = () => {
    resetCategoryWizard();
    setSubmitError(null);
    openCategoryWizard();
  };

  const handleCategoryWizardNext = () => {
    if (categoryWizardStep === 0) {
      if (!cwName.trim()) {
        setSubmitError("Укажите название категории");
        return;
      }
      setSubmitError(null);
      setCwRoleCodes((prev) => {
        if (prev.length > 0) return prev;
        const picked = pickDefaultRoleCodes(rbacCatalog?.roles);
        return picked.length ? picked : prev;
      });
      setCategoryWizardStep(1);
      return;
    }
  };

  const handleCategoryWizardSubmit = () => {
    if (cwRoleCodes.length < 1) {
      setSubmitError("Выберите хотя бы одну роль для типового профиля категории");
      return;
    }
    if (!clinicId) return;
    setSubmitError(null);
    createCat.mutate(
      { name: cwName.trim(), sort_order: cwSortOrder, default_role_codes: cwRoleCodes },
      {
        onSuccess: () => {
          closeCategoryWizard();
          resetCategoryWizard();
          setSubmitError(null);
        },
        onError: (e) => setSubmitError(humanizeStaffDirectoryError(e)),
      }
    );
  };

  const resetStaffWizard = () => {
    setStaffWizardStep(0);
    setSwEmail("");
    setSwPassword("");
    setSwFullName("");
    setSwBirthDate("");
    setSwProfessionCategoryId(null);
    setSwRoleCodes([]);
  };

  const handleOpenStaffWizard = () => {
    resetStaffWizard();
    setSubmitError(null);
    openStaffWizard();
  };

  const handleStaffWizardNext = () => {
    if (staffWizardStep === 0) {
      if (!clinicId) {
        setSubmitError("Выберите клинику");
        return;
      }
      if (!swEmail.trim()) {
        setSubmitError("Укажите email");
        return;
      }
      if (swPassword.length < MIN_PASSWORD_LENGTH) {
        setSubmitError(`Пароль не менее ${MIN_PASSWORD_LENGTH} символов`);
        return;
      }
      setSubmitError(null);
      setStaffWizardStep(1);
      return;
    }
    if (staffWizardStep === 1) {
      const cat = (categories ?? []).find((c) => c.id === swProfessionCategoryId);
      const fromTemplate = cat?.default_role_codes?.length ? [...cat.default_role_codes] : [];
      setSwRoleCodes(
        fromTemplate.length > 0 ? fromTemplate : pickDefaultRoleCodes(rbacCatalog?.roles)
      );
      setSubmitError(null);
      setStaffWizardStep(2);
    }
  };

  const handleStaffWizardBack = () => {
    if (staffWizardStep > 0) {
      setStaffWizardStep((s) => s - 1);
      setSubmitError(null);
    }
  };

  const handleStaffWizardSubmit = () => {
    if (swRoleCodes.length < 1) {
      setSubmitError("Выберите хотя бы одну роль для учётной записи");
      return;
    }
    if (!clinicId) return;
    setSubmitError(null);
    createMut.mutate(
      {
        email: swEmail.trim(),
        password: swPassword,
        full_name: swFullName.trim() || null,
        birth_date: swBirthDate.trim() || null,
        profession_category_id: swProfessionCategoryId,
        role_codes: swRoleCodes,
      },
      {
        onSuccess: () => {
          closeStaffWizard();
          resetStaffWizard();
          setSubmitError(null);
        },
        onError: (e) => setSubmitError(humanizeStaffDirectoryError(e)),
      }
    );
  };

  const openEditCategory = (row: StaffProfessionCategoryRow) => {
    setEditCategoryRow(row);
    setEcName(row.name);
    setEcSortOrder(row.sort_order);
    setEcRoleCodes(row.default_role_codes?.length ? [...row.default_role_codes] : []);
    setSubmitError(null);
  };

  const saveEditCategory = () => {
    if (!editCategoryRow || !clinicId) return;
    if (!ecName.trim()) {
      setSubmitError("Укажите название");
      return;
    }
    if (ecRoleCodes.length < 1) {
      setSubmitError("Нужна хотя бы одна роль");
      return;
    }
    setSubmitError(null);
    patchCat.mutate(
      {
        categoryId: editCategoryRow.id,
        name: ecName.trim(),
        sort_order: ecSortOrder,
        default_role_codes: ecRoleCodes,
      },
      {
        onSuccess: () => {
          setEditCategoryRow(null);
          setSubmitError(null);
        },
        onError: (e) => setSubmitError(humanizeStaffDirectoryError(e)),
      }
    );
  };

  const openCategoryModal = (row: StaffDirectoryAdminRow) => {
    setCategoryEdit(row);
    setCategoryDraft(row.profession_category_id);
    setEmploymentError(null);
  };

  const saveCategoryModal = () => {
    if (!categoryEdit) return;
    patchStaff.mutate(
      { adminId: categoryEdit.id, profession_category_id: categoryDraft },
      {
        onSuccess: () => {
          setCategoryEdit(null);
          setCategoryDraft(null);
        },
        onError: (e) =>
          setEmploymentError(e instanceof Error ? e.message : "Не удалось сохранить категорию"),
      }
    );
  };

  const expandLabel = useMemo(() => {
    if (!expandModalTab) return "";
    if (expandModalTab === TAB_ALL) return "Все сотрудники";
    if (expandModalTab === TAB_NONE) return "Без категории";
    const id = parseCategoryTab(expandModalTab);
    const name = (categories ?? []).find((c) => c.id === id)?.name;
    return name ?? "Категория";
  }, [expandModalTab, categories]);

  const expandList = expandModalTab ? filteredForTab(expandModalTab) : [];

  const renderStaffTable = (rows: StaffDirectoryAdminRow[], opts?: { compact?: boolean }) => {
    const compact = opts?.compact ?? false;
    return (
      <Table withTableBorder withRowBorders highlightOnHover verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Email</Table.Th>
            <Table.Th>ФИО</Table.Th>
            {!compact && <Table.Th>Категория</Table.Th>}
            <Table.Th>Дата рождения</Table.Th>
            <Table.Th>Статус</Table.Th>
            <Table.Th>Права</Table.Th>
            <Table.Th style={{ width: compact ? 120 : 52 }} />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((a) => {
            const isSelf = Boolean(currentAdminId && a.id === currentAdminId);
            const isTerminated = a.employment_status === "terminated";
            const rowPatching = patchStaff.isPending && patchStaff.variables?.adminId === a.id;
            return (
              <Table.Tr key={a.id}>
                <Table.Td>{a.email}</Table.Td>
                <Table.Td>{a.full_name ?? "—"}</Table.Td>
                {!compact && (
                  <Table.Td>
                    <Group gap="xs" wrap="nowrap">
                      <Text size="sm" lineClamp={1} maw={160}>
                        {a.profession_category_name ?? "—"}
                      </Text>
                      <Tooltip
                        label={
                          categorySelectData.length === 0
                            ? "Сначала создайте категории профессий выше"
                            : "Изменить категорию"
                        }
                      >
                        <ActionIcon
                          variant="light"
                          size="sm"
                          aria-label="Изменить категорию"
                          onClick={() => openCategoryModal(a)}
                          disabled={categorySelectData.length === 0}
                        >
                          <IconPencil size={16} />
                        </ActionIcon>
                      </Tooltip>
                    </Group>
                  </Table.Td>
                )}
                <Table.Td>{a.birth_date ?? "—"}</Table.Td>
                <Table.Td>
                  <Badge size="sm" variant="light" color={isTerminated ? "gray" : "green"}>
                    {isTerminated ? "Уволен" : "Активен"}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Button
                    component={Link}
                    to={`${ROUTE_PATHS.admin.rightsPolicies}?user=${encodeURIComponent(a.id)}`}
                    size="xs"
                    variant="light"
                    leftSection={<IconExternalLink size={14} />}
                  >
                    Права
                  </Button>
                </Table.Td>
                <Table.Td>
                  {isSelf ? (
                    <Text size="xs" c="dimmed" title="Увольнение себя недоступно">
                      —
                    </Text>
                  ) : (
                    <Menu position="bottom-end" withArrow>
                      <Menu.Target>
                        <ActionIcon
                          variant="subtle"
                          size="sm"
                          aria-label="Действия"
                          loading={rowPatching}
                          disabled={rowPatching}
                        >
                          <IconDotsVertical size={16} />
                        </ActionIcon>
                      </Menu.Target>
                      <Menu.Dropdown>
                        {!isTerminated ? (
                          <Menu.Item
                            color="red"
                            onClick={() => {
                              setEmploymentError(null);
                              patchStaff.mutate(
                                { adminId: a.id, employment_status: "terminated" },
                                {
                                  onError: (e) =>
                                    setEmploymentError(
                                      e instanceof Error ? e.message : "Не удалось уволить"
                                    ),
                                }
                              );
                            }}
                          >
                            Уволить
                          </Menu.Item>
                        ) : (
                          <Menu.Item
                            onClick={() => {
                              setEmploymentError(null);
                              patchStaff.mutate(
                                { adminId: a.id, employment_status: "active" },
                                {
                                  onError: (e) =>
                                    setEmploymentError(
                                      e instanceof Error ? e.message : "Не удалось восстановить"
                                    ),
                                }
                              );
                            }}
                          >
                            Восстановить
                          </Menu.Item>
                        )}
                      </Menu.Dropdown>
                    </Menu>
                  )}
                </Table.Td>
              </Table.Tr>
            );
          })}
        </Table.Tbody>
      </Table>
    );
  };

  const rbacLoading = Boolean(clinicId) && !rbacCatalog && !rbacCatalogError;

  return (
    <Stack gap="lg">
      <ContextBar title="Персонал" />
      <Stack gap="xs">
        <Group justify="space-between" align="flex-start" wrap="wrap">
          <div>
            <Title order={3}>Каталог персонала клиники</Title>
            <Text size="sm" c="dimmed" maw={720}>
              Enterprise: категории задают типовые роли; у каждого сотрудника — свои роли при создании. Вкладки и
              фильтр по клинике изолируют данные. Тонкая настройка прав — в «Права и политики».
            </Text>
          </div>
          <Badge variant="light" color="blue" size="lg">
            RBAC + категории
          </Badge>
        </Group>
        {rbacLoading && (
          <Group gap="xs">
            <Loader size="sm" />
            <Text size="xs" c="dimmed">
              Загружаем каталог ролей для выбранной клиники…
            </Text>
          </Group>
        )}
      </Stack>

      <Paper p="lg" withBorder shadow="xs" radius="md" className="data-toolbar-card">
        <Stack gap="sm">
          <Text fw={600} size="sm">
            Контекст клиники
          </Text>
          <Select
            data={clinicOptions}
            value={clinicId}
            onChange={(v) => setCurrentClinicId(v)}
            placeholder="Выберите клинику"
            searchable
            comboboxProps={{ withinPortal: true }}
            description="Все операции ниже относятся только к этой клинике."
          />
        </Stack>
      </Paper>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <Paper p="lg" withBorder shadow="xs" radius="md" className="data-toolbar-card">
          <Stack gap="md">
            <Group justify="space-between" align="center" wrap="nowrap">
              <Group gap="sm">
                <ThemeIcon size="lg" variant="light" color="blue" radius="md">
                  <IconBriefcase size={20} />
                </ThemeIcon>
                <div>
                  <Text fw={700} size="sm">
                    Категории профессий
                  </Text>
                  <Text size="xs" c="dimmed">
                    Названия и типовые роли (врачи, администраторы…). Не зависят от шаблона типа бизнеса.
                  </Text>
                </div>
              </Group>
            </Group>
            <Divider />
          {catError && <QueryErrorAlert error={catErr} />}
          <Button
            onClick={handleOpenCategoryWizard}
            disabled={!clinicId || rbacLoading}
            leftSection={<IconBriefcase size={18} />}
            size="md"
            fullWidth
          >
            Создать категорию (2 шага: название → типовые роли)
          </Button>
          {catLoading && <PageSkeleton variant="table" rows={2} />}
          {!catLoading && (categories ?? []).length > 0 && (
            <Table withTableBorder withRowBorders verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Название</Table.Th>
                  <Table.Th>Типовые роли</Table.Th>
                  <Table.Th style={{ width: 88 }} />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(categories ?? []).map((c) => (
                  <Table.Tr key={c.id}>
                    <Table.Td>{c.name}</Table.Td>
                    <Table.Td>
                      <Text size="xs" lineClamp={2}>
                        {(c.default_role_codes ?? []).join(", ") || "—"}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Group gap={4} wrap="nowrap">
                        <Tooltip label="Изменить категорию и типовые роли">
                          <ActionIcon
                            variant="light"
                            size="sm"
                            aria-label="Редактировать категорию"
                            onClick={() => openEditCategory(c)}
                          >
                            <IconPencil size={16} />
                          </ActionIcon>
                        </Tooltip>
                        <ActionIcon
                          variant="subtle"
                          color="red"
                          size="sm"
                          aria-label="Удалить категорию"
                          loading={deleteCat.isPending}
                          onClick={() => deleteCat.mutate(c.id)}
                        >
                          ×
                        </ActionIcon>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
          {!catLoading && (categories ?? []).length === 0 && (
            <Text size="sm" c="dimmed">
              Нет категорий. Создайте первую кнопкой выше — роли выбираются на втором шаге мастера.
            </Text>
          )}
          </Stack>
        </Paper>

        <Paper p="lg" withBorder shadow="xs" radius="md" className="data-toolbar-card">
          <Stack gap="md">
            <Group gap="sm">
              <ThemeIcon size="lg" variant="light" color="teal" radius="md">
                <IconUsersPlus size={20} />
              </ThemeIcon>
              <div>
                <Text fw={700} size="sm">
                  Новый сотрудник
                </Text>
                <Text size="xs" c="dimmed">
                  3 шага: логин → категория (опционально) → роли учётной записи (обязательно).
                </Text>
              </div>
            </Group>
            <Divider />
            <Button
              onClick={handleOpenStaffWizard}
              disabled={!clinicId || rbacLoading}
              leftSection={<IconUsersPlus size={18} />}
              size="md"
              color="teal"
              fullWidth
            >
              Добавить сотрудника
            </Button>
          </Stack>
        </Paper>
      </SimpleGrid>

      <Paper p="lg" withBorder shadow="xs" radius="md" className="data-table-card">
        <Group justify="space-between" mb="xs" wrap="wrap">
          <Text fw={700} size="md">
            Сотрудники выбранной клиники
          </Text>
          {list.length > 0 && staffTab !== TAB_ALL && (
            <Button
              size="xs"
              variant="light"
              onClick={() => {
                setExpandModalTab(staffTab);
                openExpand();
              }}
            >
              Открыть список в окне
            </Button>
          )}
        </Group>

        {employmentError && (
          <Alert color="red" mb="sm" onClose={() => setEmploymentError(null)} withCloseButton>
            {employmentError}
          </Alert>
        )}

        {loading && <PageSkeleton variant="table" rows={4} />}
        {staffError && <QueryErrorAlert error={staffErr} />}
        {!loading && !staffError && list.length === 0 && (
          <Text size="sm" c="dimmed">
            Нет сотрудников. Добавьте первого выше.
          </Text>
        )}

        {!loading && !staffError && list.length > 0 && (
          <Tabs value={staffTab} onChange={(v) => setStaffTab(v ?? TAB_ALL)}>
            <Tabs.List>
              <Tabs.Tab value={TAB_ALL}>Все ({counts.all})</Tabs.Tab>
              <Tabs.Tab value={TAB_NONE}>Без категории ({counts.none})</Tabs.Tab>
              {(categories ?? []).map((c) => (
                <Tabs.Tab key={c.id} value={tabValueForCategory(c.id)}>
                  {c.name} ({counts.byCat[c.id] ?? 0})
                </Tabs.Tab>
              ))}
            </Tabs.List>

            <Tabs.Panel value={TAB_ALL} pt="md">
              {renderStaffTable(filteredForTab(TAB_ALL))}
            </Tabs.Panel>
            <Tabs.Panel value={TAB_NONE} pt="md">
              {filteredForTab(TAB_NONE).length === 0 ? (
                <Text size="sm" c="dimmed">
                  Нет сотрудников без категории на этой вкладке.
                </Text>
              ) : (
                renderStaffTable(filteredForTab(TAB_NONE))
              )}
            </Tabs.Panel>
            {(categories ?? []).map((c) => {
              const tv = tabValueForCategory(c.id);
              const rows = filteredForTab(tv);
              return (
                <Tabs.Panel key={c.id} value={tv} pt="md">
                  {rows.length === 0 ? (
                    <Text size="sm" c="dimmed">
                      Нет сотрудников в этой категории.
                    </Text>
                  ) : (
                    renderStaffTable(rows)
                  )}
                </Tabs.Panel>
              );
            })}
          </Tabs>
        )}
      </Paper>

      <Modal
        opened={Boolean(categoryEdit)}
        onClose={() => {
          setCategoryEdit(null);
          setCategoryDraft(null);
        }}
        title="Категория профессии"
        centered
      >
        {categoryEdit && (
          <Stack gap="md">
            <Text size="sm">
              {categoryEdit.full_name ?? categoryEdit.email}
            </Text>
            <Select
              label="Категория"
              placeholder="Не выбрано"
              clearable
              data={categorySelectData}
              value={categoryDraft}
              onChange={setCategoryDraft}
              disabled={categorySelectData.length === 0}
              comboboxProps={{ withinPortal: true }}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setCategoryEdit(null)}>
                Отмена
              </Button>
              <Button
                loading={patchStaff.isPending}
                onClick={saveCategoryModal}
                disabled={categorySelectData.length === 0}
              >
                Сохранить
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      <Modal opened={expandOpened} onClose={closeExpand} title={expandLabel} size="xl" centered>
        <ScrollArea h={480} type="auto">
          {expandList.length === 0 ? (
            <Text size="sm" c="dimmed">
              Нет записей.
            </Text>
          ) : (
            renderStaffTable(expandList, {
              compact: Boolean(expandModalTab?.startsWith("cat:")),
            })
          )}
        </ScrollArea>
      </Modal>

      <Modal
        opened={categoryWizardOpen}
        onClose={() => {
          closeCategoryWizard();
          resetCategoryWizard();
          setSubmitError(null);
        }}
        title={
          <Text fw={600}>
            Новая категория профессии{" "}
            <Text span c="dimmed" size="sm" fw={400}>
              (шаг {categoryWizardStep + 1} из 2)
            </Text>
          </Text>
        }
        size="lg"
        centered
      >
        <Stack gap="md">
          {submitError && (
            <Alert color="red" onClose={() => setSubmitError(null)} withCloseButton>
              {submitError}
            </Alert>
          )}
          {rbacCatalogError && (
            <Alert color="orange" title="Каталог ролей недоступен">
              {rbacCatalogErr instanceof Error ? rbacCatalogErr.message : "Ошибка загрузки"}. Для выбора ролей нужны
              права «Управление RBAC» (rbac.manage).
            </Alert>
          )}
          <Progress value={(categoryWizardStep + 1) * 50} size="sm" />
          <Stepper
            active={categoryWizardStep}
            onStepClick={setCategoryWizardStep}
            allowNextStepsSelect={false}
            iconSize={32}
          >
            <Stepper.Step label="Название" description="Как в списке и вкладках">
              <Stack gap="sm" pt="md">
                <TextInput
                  label="Название категории"
                  value={cwName}
                  onChange={(e) => setCwName(e.currentTarget.value)}
                  placeholder="Например: Врачи, Администраторы"
                  required
                />
                <NumberInput
                  label="Порядок сортировки"
                  value={cwSortOrder}
                  onChange={(v) => setCwSortOrder(typeof v === "number" ? v : Number(v) || 0)}
                  min={0}
                />
                <Group justify="flex-end">
                  <Button
                    variant="default"
                    onClick={() => {
                      closeCategoryWizard();
                      resetCategoryWizard();
                      setSubmitError(null);
                    }}
                  >
                    Отмена
                  </Button>
                  <Button onClick={handleCategoryWizardNext}>Далее: типовые роли</Button>
                </Group>
              </Stack>
            </Stepper.Step>
            <Stepper.Step label="Типовые роли" description="Обязательно для API">
              <Stack gap="sm" pt="md">
                <Text size="sm" c="dimmed">
                  Совпадают с ролями RBAC клиники. После сохранения шаблон можно менять карандашом в таблице — роли
                  пересоберутся у всех сотрудников категории (роль владельца сохраняется).
                </Text>
                <MultiSelect
                  label="Типовые роли категории"
                  placeholder="Выберите одну или несколько ролей"
                  description="По умолчанию подставляются рекомендуемые роли из каталога — при необходимости измените."
                  data={roleCatalogOptions}
                  value={cwRoleCodes}
                  onChange={setCwRoleCodes}
                  searchable
                  nothingFoundMessage="Нет ролей — проверьте права rbac.manage и выбранную клинику"
                  comboboxProps={{ withinPortal: true }}
                />
                <Group justify="flex-end">
                  <Button
                    variant="default"
                    onClick={() => {
                      setCategoryWizardStep(0);
                      setSubmitError(null);
                    }}
                  >
                    Назад
                  </Button>
                  <Button onClick={handleCategoryWizardSubmit} loading={createCat.isPending}>
                    Создать категорию
                  </Button>
                </Group>
              </Stack>
            </Stepper.Step>
          </Stepper>
        </Stack>
      </Modal>

      <Modal
        opened={staffWizardOpen}
        onClose={() => {
          closeStaffWizard();
          resetStaffWizard();
          setSubmitError(null);
        }}
        title={
          <Text fw={600}>
            Новый сотрудник{" "}
            <Text span c="dimmed" size="sm" fw={400}>
              (шаг {staffWizardStep + 1} из 3)
            </Text>
          </Text>
        }
        size="lg"
        centered
      >
        <Stack gap="md">
          {submitError && (
            <Alert color="red" onClose={() => setSubmitError(null)} withCloseButton>
              {submitError}
            </Alert>
          )}
          {rbacCatalogError && staffWizardStep === 2 && (
            <Alert color="orange" title="Каталог ролей недоступен">
              {rbacCatalogErr instanceof Error ? rbacCatalogErr.message : "Ошибка загрузки"}.
            </Alert>
          )}
          <Progress value={((staffWizardStep + 1) / 3) * 100} size="sm" />
          <Stepper
            active={staffWizardStep}
            onStepClick={setStaffWizardStep}
            allowNextStepsSelect={false}
            iconSize={32}
          >
            <Stepper.Step label="Учётная запись" description="Email и пароль">
              <Stack gap="sm" pt="md">
                <TextInput
                  label="Email"
                  type="email"
                  value={swEmail}
                  onChange={(e) => setSwEmail(e.currentTarget.value)}
                  placeholder="staff@example.com"
                  required
                />
                <TextInput
                  label="Пароль"
                  type="password"
                  value={swPassword}
                  onChange={(e) => setSwPassword(e.currentTarget.value)}
                  minLength={MIN_PASSWORD_LENGTH}
                  description={`Не менее ${MIN_PASSWORD_LENGTH} символов`}
                />
                <TextInput
                  label="ФИО"
                  value={swFullName}
                  onChange={(e) => setSwFullName(e.currentTarget.value)}
                />
                <TextInput
                  label="Дата рождения"
                  type="date"
                  value={swBirthDate}
                  onChange={(e) => setSwBirthDate(e.currentTarget.value)}
                />
                <Group justify="flex-end">
                  <Button
                    variant="default"
                    onClick={() => {
                      closeStaffWizard();
                      resetStaffWizard();
                      setSubmitError(null);
                    }}
                  >
                    Отмена
                  </Button>
                  <Button onClick={handleStaffWizardNext}>Далее: категория</Button>
                </Group>
              </Stack>
            </Stepper.Step>
            <Stepper.Step label="Категория" description="Необязательно">
              <Stack gap="sm" pt="md">
                <Text size="sm" c="dimmed">
                  Можно пропустить. На следующем шаге роли подставятся из типовых ролей категории или из каталога.
                </Text>
                <Select
                  label="Категория профессии"
                  placeholder="Не выбрано"
                  clearable
                  data={categorySelectData}
                  value={swProfessionCategoryId}
                  onChange={setSwProfessionCategoryId}
                  disabled={categorySelectData.length === 0}
                  comboboxProps={{ withinPortal: true }}
                />
                <Group justify="flex-end">
                  <Button variant="default" onClick={handleStaffWizardBack}>
                    Назад
                  </Button>
                  <Button onClick={handleStaffWizardNext}>Далее: роли</Button>
                </Group>
              </Stack>
            </Stepper.Step>
            <Stepper.Step label="Роли" description="Обязательно для входа">
              <Stack gap="sm" pt="md">
                <MultiSelect
                  label="Роли учётной записи"
                  placeholder="Выберите роли"
                  description="Без ролей сотрудник не получит доступ в админку. Можно скорректировать позже в «Права и политики»."
                  data={roleCatalogOptions}
                  value={swRoleCodes}
                  onChange={setSwRoleCodes}
                  searchable
                  nothingFoundMessage="Нет ролей в каталоге"
                  comboboxProps={{ withinPortal: true }}
                />
                <Group justify="flex-end">
                  <Button variant="default" onClick={handleStaffWizardBack}>
                    Назад
                  </Button>
                  <Button onClick={handleStaffWizardSubmit} loading={createMut.isPending}>
                    Создать учётную запись
                  </Button>
                </Group>
              </Stack>
            </Stepper.Step>
          </Stepper>
        </Stack>
      </Modal>

      <Modal
        opened={Boolean(editCategoryRow)}
        onClose={() => {
          setEditCategoryRow(null);
          setSubmitError(null);
        }}
        title="Редактирование категории"
        size="lg"
        centered
      >
        {editCategoryRow && (
          <Stack gap="md">
            {submitError && (
              <Alert color="red" onClose={() => setSubmitError(null)} withCloseButton>
                {submitError}
              </Alert>
            )}
            {JSON.stringify([...ecRoleCodes].sort()) !==
              JSON.stringify([...(editCategoryRow.default_role_codes ?? [])].sort()) && (
              <Alert color="orange" title="Синхронизация ролей">
                После сохранения набор ролей будет пересобран у всех сотрудников этой категории (кроме сохранения роли
                владельца, если она есть).
              </Alert>
            )}
            {rbacCatalogError && (
              <Alert color="orange" title="Каталог ролей недоступен">
                {rbacCatalogErr instanceof Error ? rbacCatalogErr.message : "Ошибка загрузки"}.
              </Alert>
            )}
            <TextInput label="Название" value={ecName} onChange={(e) => setEcName(e.currentTarget.value)} />
            <NumberInput
              label="Порядок сортировки"
              value={ecSortOrder}
              onChange={(v) => setEcSortOrder(typeof v === "number" ? v : Number(v) || 0)}
              min={0}
            />
            <MultiSelect
              label="Типовые роли"
              data={roleCatalogOptions}
              value={ecRoleCodes}
              onChange={setEcRoleCodes}
              searchable
              comboboxProps={{ withinPortal: true }}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setEditCategoryRow(null)}>
                Отмена
              </Button>
              <Button onClick={saveEditCategory} loading={patchCat.isPending}>
                Сохранить
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
