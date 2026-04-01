import type { UiLocale } from "@/admin/rbacDomainGlossary";

export interface RbacRightsPoliciesCopy {
  pageTitle: string;
  intro: string;
  languageLabel: string;
  langRu: string;
  langEn: string;
  domainHelpTitle: string;
  domainHelpP1: string;
  domainHelpP2: string;
  domainHelpP3: string;
  safeTitle: string;
  safeStep1: string;
  safeStep2: string;
  safeStep3: string;
  glossaryTitle: string;
  glossaryRole: string;
  glossaryPermission: string;
  glossaryGrant: string;
  glossaryDeny: string;
  glossaryDomain: string;
  tabRoles: string;
  tabUsers: string;
  tabPolicies: string;
  tabAudit: string;
  rolesPanelTitle: string;
  rolesPanelBody: string;
  /** Блок «создать роль» под вводным Alert */
  rolesPanelCreateBlockTitle: string;
  rolesPanelCreateBlockHint: string;
  labelRole: string;
  phRole: string;
  labelDomain: string;
  labelSearch: string;
  phSearchRoles: string;
  phSearchUsers: string;
  tipDomainFilter: string;
  labelRolePermissions: string;
  ownerRoleProtectedTitle: string;
  ownerRoleProtectedBody: string;
  diffRole: string;
  noChanges: string;
  saveRolePermissions: string;
  usersPanelTitle: string;
  usersPanelBody: string;
  labelEmployee: string;
  phEmployee: string;
  labelUserRoles: string;
  ownerUserProtectedTitle: string;
  ownerUserProtectedBody: string;
  diffUserRoles: string;
  saveUserRoles: string;
  labelGrant: string;
  labelDeny: string;
  ownerOverridesTitle: string;
  ownerOverridesBody: string;
  grantDenyGuideTitle: string;
  grantDenyGuide1: string;
  grantDenyGuide2: string;
  grantDenyGuide3: string;
  diffGrant: string;
  diffDeny: string;
  saveUserPermissions: string;
  effectivePermissions: string;
  policiesPanelTitle: string;
  policiesPanelBody: string;
  swDiscount: string;
  swReminders: string;
  swAllNotif: string;
  swMorningBrief: string;
  labelMorningBriefTime: string;
  labelOwnerTg: string;
  swAiSupervisor: string;
  labelAiSupervisorTime: string;
  labelAiSupervisorRecipients: string;
  diffPolicies: string;
  savePolicies: string;
  auditPanelTitle: string;
  auditPanelBody: string;
  auditWhen: string;
  auditWho: string;
  auditAction: string;
  auditEntity: string;
  auditNote: string;
  glossarySectionTitle: string;
  glossarySectionSubtitle: string;
  csvDomains: string;
  csvPermissions: string;
  glossaryToggleShow: string;
  glossaryToggleHide: string;
  glossaryEmpty: string;
  thReadName: string;
  thExplanation: string;
  thAllCodes: string;
  thSystemKey: string;
  modalConfirm: string;
  modalCriticalLabel: string;
  cancel: string;
  apply: string;
  noAccessTitle: string;
  noAccessBody: string;
  badgeNoDescription: string;
  permDescCatalogRu: string;
  /** Пусто для RU; для EN — напоминание, что текст в каталоге на русском */
  catalogDescriptionLanguageNote: string;
  roleCodeTooltip: string;
  criticalOwnerRole: string;
  criticalOwnerRoleMsg: string;
  criticalSelfRole: string;
  criticalSelfRoleMsg: string;
  criticalSelfRbac: string;
  criticalSelfRbacMsg: string;
  tableField: string;
  tableBefore: string;
  tableAfter: string;
  /** Создание кастомной роли клиники */
  btnCreateClinicRole: string;
  modalCreateRoleTitle: string;
  labelNewRoleCode: string;
  phNewRoleCode: string;
  labelNewRoleName: string;
  phNewRoleName: string;
  labelPermissionPreset: string;
  optPresetNone: string;
  presetLabelManager: string;
  presetLabelAdmin: string;
  presetLabelDoctor: string;
  labelFillFromRole: string;
  optFillFromRoleNone: string;
  hintCreateRolePermissions: string;
  labelCreateRoleNote: string;
  phCreateRoleNote: string;
  btnSubmitNewRole: string;
  errCreateRoleCode: string;
  errCreateRoleName: string;
  errCreateRolePerms: string;
  btnDeleteClinicRole: string;
  modalDeleteRoleTitle: string;
  modalDeleteRoleBody: string;
  confirmDeleteRole: string;
}

const RU: RbacRightsPoliciesCopy = {
  pageTitle: "Права и политики",
  intro:
    "Здесь вы настраиваете, кто и что может делать в вашем бизнесе: по ролям, по конкретным сотрудникам, по системным правилам и с полной историей изменений.",
  languageLabel: "Язык страницы",
  langRu: "Русский",
  langEn: "English",
  domainHelpTitle: "Что такое «домен»",
  domainHelpP1:
    "Домен — это не отдел вашей клиники. Это способ разложить длинный список прав по группам: система берёт первую часть кода права (до точки или до подчёркивания) и по ней объединяет строки. Так проще ориентироваться в каталоге.",
  domainHelpP2:
    "Кому вы что даёте, определяется не ярлыком домена, а конкретными строками прав в списке: у каждой есть описание. Домен помогает сузить список (например только задачи или только финансы), а точный смысл — всегда в тексте у права.",
  domainHelpP3:
    "Если видите группы вроде «Просмотр (по префиксу кода)» — это нормально: так называются права с общим началом кода (например view_). Внутри могут быть разные зоны; читайте подпись к каждой строке.",
  safeTitle: "Как работать с этой страницей безопасно",
  safeStep1: "Сначала выберите роль или сотрудника и вносите изменения небольшими шагами.",
  safeStep2: "Перед сохранением проверьте блок «Diff before save» — там точный список того, что изменится.",
  safeStep3: "После сохранения откройте вкладку «Аудит» и убедитесь, что изменения зафиксированы.",
  glossaryTitle: "Короткий глоссарий",
  glossaryRole: "Роль — набор прав для должности (например администратор, менеджер).",
  glossaryPermission: "Право — конкретное действие в системе (например видеть финансы, менять расписание).",
  glossaryGrant: "Grant — выдать сотруднику дополнительное право поверх ролей.",
  glossaryDeny: "Deny — точечно запретить право, даже если роль обычно его даёт.",
  glossaryDomain:
    "Домен — группировка по похожему началу кода права. Помогает фильтровать список; смысл каждого пункта — в его описании.",
  tabRoles: "Роли и профессии",
  tabUsers: "Сотрудники",
  tabPolicies: "Политики системы",
  tabAudit: "Аудит",
  rolesPanelTitle: "Вкладка «Роли и профессии»",
  rolesPanelBody:
    "Вы задаёте стандартный набор возможностей для должности. Все сотрудники с этой ролью получают эти права автоматически.",
  rolesPanelCreateBlockTitle: "Нужна своя должность в клинике?",
  rolesPanelCreateBlockHint:
    "Создайте роль клиники: один раз задайте код, название и права — затем назначайте её сотрудникам и в типовых ролях каталога «Персонал».",
  labelRole: "Роль",
  phRole: "Выберите роль",
  labelDomain: "Домен прав",
  labelSearch: "Быстрый поиск прав",
  phSearchRoles: "Например: tasks, finance, rbac.manage",
  phSearchUsers: "Фильтр для grant/deny",
  tipDomainFilter:
    "Совет: выберите «Домен прав», чтобы сократить список до одной группы, затем читайте описание у каждой строки — оно говорит, на что вы даёте доступ. Поиск ищет по словам. В списке сначала смысл, технический код справа; при наведении открывается подробная подсказка.",
  labelRolePermissions: "Права роли",
  ownerRoleProtectedTitle: "Роль owner защищена",
  ownerRoleProtectedBody: "Права роли owner неизменяемы на уровне системы и всегда остаются полными.",
  diffRole: "Diff before save (роль)",
  noChanges: "Изменений нет",
  saveRolePermissions: "Сохранить права роли",
  usersPanelTitle: "Вкладка «Сотрудники»",
  usersPanelBody:
    "Назначайте роли конкретному человеку и при необходимости задавайте персональные исключения через grant и deny.",
  labelEmployee: "Сотрудник",
  phEmployee: "Выберите сотрудника",
  labelUserRoles: "Роли сотрудника",
  ownerUserProtectedTitle: "Пользователь owner защищён",
  ownerUserProtectedBody: "Роли такого пользователя не меняются, чтобы исключить потерю прав владельца.",
  diffUserRoles: "Diff before save (роли сотрудника)",
  saveUserRoles: "Сохранить роли",
  labelGrant: "Персональные grant",
  labelDeny: "Персональные deny",
  ownerOverridesTitle: "Персональные исключения для owner",
  ownerOverridesBody:
    "Для пользователя с ролью owner персональные grant/deny отключены — права владельца нельзя урезать.",
  grantDenyGuideTitle: "Как использовать grant и deny",
  grantDenyGuide1: "Grant — когда человеку временно или ситуативно нужно больше прав, чем даёт роль.",
  grantDenyGuide2: "Deny — когда нужно аккуратно ограничить доступ по отдельному процессу (например финансы).",
  grantDenyGuide3: "Если сомневаетесь, начинайте с ролей; персональные настройки — для исключений.",
  diffGrant: "Diff before save (grant)",
  diffDeny: "Diff before save (deny)",
  saveUserPermissions: "Сохранить персональные права",
  effectivePermissions: "Эффективные права",
  policiesPanelTitle: "Вкладка «Политики системы»",
  policiesPanelBody:
    "Глобальные правила клиники: они влияют на поведение системы в целом, а не на одного сотрудника.",
  swDiscount: "Пациент может отключить скидочные уведомления",
  swReminders: "Пациент может отключить напоминания",
  swAllNotif: "Пациент может отключить все уведомления",
  swMorningBrief: "Включить утреннюю сводку владельцу (Owner Morning Brief)",
  labelMorningBriefTime: "Время утренней сводки (UTC, ЧЧ:ММ)",
  labelOwnerTg: "Telegram chat ID владельца",
  swAiSupervisor: "Включить AI Supervisor",
  labelAiSupervisorTime: "Время AI Supervisor (UTC, ЧЧ:ММ)",
  labelAiSupervisorRecipients: "Получатели AI Supervisor (через запятую)",
  diffPolicies: "Diff before save (политики)",
  savePolicies: "Сохранить политики",
  auditPanelTitle: "Вкладка «Аудит»",
  auditPanelBody: "История изменений прав и политик: кто, когда и что изменил.",
  auditWhen: "Когда",
  auditWho: "Кто",
  auditAction: "Действие",
  auditEntity: "Сущность",
  auditNote: "Примечание",
  glossarySectionTitle: "Справочник доменов",
  glossarySectionSubtitle:
    "Полный каталог групп прав для вашей клиники: пояснения и все коды в каждой группе. Откройте таблицу при необходимости. CSV удобен для Excel и архива.",
  csvDomains: "Скачать CSV — домены",
  csvPermissions: "Скачать CSV — все права",
  glossaryToggleShow: "Показать таблицу справочника",
  glossaryToggleHide: "Скрыть таблицу справочника",
  glossaryEmpty: "Домены пока не загружены.",
  thReadName: "Как читать название",
  thExplanation: "Пояснение",
  thAllCodes: "Все коды прав в группе",
  thSystemKey: "Ключ в системе",
  modalConfirm: "Подтверждение",
  modalCriticalLabel: "Подтверждаю критичное изменение",
  cancel: "Отмена",
  apply: "Применить",
  noAccessTitle: "Нет доступа",
  noAccessBody:
    "Для управления ролями и политиками требуется право rbac.manage.",
  badgeNoDescription: "Описание недоступно — смотрите документацию к продукту.",
  permDescCatalogRu:
    "Описание в каталоге на русском языке (как в продукте).",
  catalogDescriptionLanguageNote: "",
  roleCodeTooltip: "Роль в системе",
  criticalOwnerRole: "Подтвердите изменение прав роли owner",
  criticalOwnerRoleMsg:
    "Вы меняете права базовой роли owner. Это может изменить доступ владельца ко всем критичным разделам.",
  criticalSelfRole: "Подтвердите снятие критичной роли у себя",
  criticalSelfRoleMsg:
    "Вы снимаете с себя роль(и): {roles}. Это может лишить вас права rbac.manage и доступа к этому экрану.",
  criticalSelfRbac: "Подтвердите снятие rbac.manage у себя",
  criticalSelfRbacMsg:
    "Вы запрещаете себе право rbac.manage. После сохранения вы можете потерять доступ к этому экрану.",
  tableField: "Поле",
  tableBefore: "Было",
  tableAfter: "Станет",
  btnCreateClinicRole: "Создать роль клиники",
  modalCreateRoleTitle: "Новая роль клиники",
  labelNewRoleCode: "Код роли (латиница, уникален в клинике)",
  phNewRoleCode: "например reception_lead",
  labelNewRoleName: "Название для людей",
  phNewRoleName: "Например: Ресепшен (лид)",
  labelPermissionPreset: "Шаблон прав (подставить набор)",
  optPresetNone: "Без шаблона — выберите права вручную",
  presetLabelManager: "Как у системной роли «Менеджер»",
  presetLabelAdmin: "Как у системной роли «Администратор»",
  presetLabelDoctor: "Как у системной роли «Врач»",
  labelFillFromRole: "Или скопировать права с роли",
  optFillFromRoleNone: "Не копировать",
  hintCreateRolePermissions:
    "Обязательно выберите хотя бы одно право. Шаблон и копирование только подставляют список — перед сохранением проверьте и отредактируйте.",
  labelCreateRoleNote: "Комментарий в аудит (необязательно)",
  phCreateRoleNote: "Зачем создаём роль",
  btnSubmitNewRole: "Создать роль",
  errCreateRoleCode:
    "Код роли: латиница в нижнем регистре, цифры и подчёркивания, начинается с буквы. Нельзя использовать коды системных ролей.",
  errCreateRoleName: "Укажите название роли.",
  errCreateRolePerms: "Выберите хотя бы одно право.",
  btnDeleteClinicRole: "Удалить роль клиники",
  modalDeleteRoleTitle: "Удалить роль клиники?",
  modalDeleteRoleBody:
    "Удаляется только роль вашей клиники (не системные роли). Пока к роли привязаны сотрудники, удаление недоступно — снимите роль в разделе «Сотрудники».",
  confirmDeleteRole: "Удалить",
};

const EN: RbacRightsPoliciesCopy = {
  pageTitle: "Access rights & policies",
  intro:
    "Configure who can do what in your organization: by role, by individual staff member, via system-wide policies, with a full audit trail.",
  languageLabel: "Page language",
  langRu: "Russian",
  langEn: "English",
  domainHelpTitle: "What a “domain” is",
  domainHelpP1:
    "A domain is not a department in your clinic. It is a way to group a long permission list: the system takes the first segment of the permission code (before “.” or “_”) and groups rows together so the catalog is easier to scan.",
  domainHelpP2:
    "What access you grant is defined by each permission row and its description—not by the domain label alone. Domains help you filter the list; the exact meaning is always in the row text.",
  domainHelpP3:
    'If you see labels like “View (code prefix)”, that is expected: it means permissions share a common code prefix (e.g. view_). Business areas inside may differ—read each row.',
  safeTitle: "How to use this page safely",
  safeStep1: "Pick one role or one employee at a time and change settings in small steps.",
  safeStep2: 'Review the “Diff before save” block—it lists exactly what will change.',
  safeStep3: 'After saving, open the “Audit” tab and confirm the change was recorded.',
  glossaryTitle: "Short glossary",
  glossaryRole: "Role — a template of permissions for a job title (e.g. administrator, manager).",
  glossaryPermission: "Permission — one concrete action (e.g. view finance, edit schedule).",
  glossaryGrant: "Grant — add an extra permission on top of the user’s roles.",
  glossaryDeny: "Deny — explicitly block a permission even if a role would allow it.",
  glossaryDomain:
    "Domain — a grouping by similar code prefix. Helps filter the list; each item’s meaning is in its description.",
  tabRoles: "Roles & job profiles",
  tabUsers: "Staff",
  tabPolicies: "System policies",
  tabAudit: "Audit",
  rolesPanelTitle: "Tab: Roles & job profiles",
  rolesPanelBody:
    "You define the standard capability set for a job title. Everyone with that role receives these permissions automatically.",
  rolesPanelCreateBlockTitle: "Need a custom job title for your clinic?",
  rolesPanelCreateBlockHint:
    "Create a clinic role once: set code, display name, and permissions — then assign it to staff and use it in the Personnel catalog.",
  labelRole: "Role",
  phRole: "Select a role",
  labelDomain: "Permission domain",
  labelSearch: "Quick search",
  phSearchRoles: "e.g. tasks, finance, rbac.manage",
  phSearchUsers: "Filter for grant/deny",
  tipDomainFilter:
    "Tip: choose a domain to narrow the list to one group, then read each row’s description—it states what access you grant. Search matches text. In the list, meaning comes first and the technical code is on the right; hover for details.",
  labelRolePermissions: "Role permissions",
  ownerRoleProtectedTitle: "Owner role is protected",
  ownerRoleProtectedBody: "Owner role permissions are fixed at system level and always remain full.",
  diffRole: "Diff before save (role)",
  noChanges: "No changes",
  saveRolePermissions: "Save role permissions",
  usersPanelTitle: "Tab: Staff",
  usersPanelBody:
    "Assign roles to a specific person and, if needed, set personal overrides with grant and deny.",
  labelEmployee: "Employee",
  phEmployee: "Select an employee",
  labelUserRoles: "Staff roles",
  ownerUserProtectedTitle: "Owner user is protected",
  ownerUserProtectedBody: "This user’s roles cannot be changed, to avoid removing owner access.",
  diffUserRoles: "Diff before save (staff roles)",
  saveUserRoles: "Save roles",
  labelGrant: "Personal grants",
  labelDeny: "Personal denials",
  ownerOverridesTitle: "Personal overrides for owner",
  ownerOverridesBody:
    "Personal grant/deny is disabled for an owner user—owner permissions cannot be reduced.",
  grantDenyGuideTitle: "Using grant and deny",
  grantDenyGuide1: "Grant — when someone temporarily needs more access than their role provides.",
  grantDenyGuide2: "Deny — when you need to restrict a specific workflow (e.g. finance).",
  grantDenyGuide3: "If unsure, start with roles; use personal overrides only as exceptions.",
  diffGrant: "Diff before save (grant)",
  diffDeny: "Diff before save (deny)",
  saveUserPermissions: "Save personal permissions",
  effectivePermissions: "Effective permissions",
  policiesPanelTitle: "Tab: System policies",
  policiesPanelBody:
    "Clinic-wide rules that affect overall system behaviour, not a single employee.",
  swDiscount: "Patient can turn off discount notifications",
  swReminders: "Patient can turn off reminders",
  swAllNotif: "Patient can turn off all notifications",
  swMorningBrief: "Enable owner morning brief",
  labelMorningBriefTime: "Morning brief time (UTC, HH:MM)",
  labelOwnerTg: "Owner Telegram chat ID",
  swAiSupervisor: "Enable AI Supervisor",
  labelAiSupervisorTime: "AI Supervisor time (UTC, HH:MM)",
  labelAiSupervisorRecipients: "AI Supervisor recipients (comma-separated)",
  diffPolicies: "Diff before save (policies)",
  savePolicies: "Save policies",
  auditPanelTitle: "Tab: Audit",
  auditPanelBody: "History of permission and policy changes: who changed what and when.",
  auditWhen: "When",
  auditWho: "Who",
  auditAction: "Action",
  auditEntity: "Entity",
  auditNote: "Note",
  glossarySectionTitle: "Domain reference",
  glossarySectionSubtitle:
    "Full catalog of permission groups for your clinic: explanations and every code in each group. Open the table when needed. CSV works in Excel and for archiving.",
  csvDomains: "Download CSV — domains",
  csvPermissions: "Download CSV — all permissions",
  glossaryToggleShow: "Show reference table",
  glossaryToggleHide: "Hide reference table",
  glossaryEmpty: "Domains are not loaded yet.",
  thReadName: "How to read the name",
  thExplanation: "Explanation",
  thAllCodes: "All permission codes in group",
  thSystemKey: "System key",
  modalConfirm: "Confirmation",
  modalCriticalLabel: "I confirm this critical change",
  cancel: "Cancel",
  apply: "Apply",
  noAccessTitle: "Access denied",
  noAccessBody: "Managing roles and policies requires the rbac.manage permission.",
  badgeNoDescription: "No description in catalog—see product documentation.",
  permDescCatalogRu: "Catalog description (Russian, as shipped in the product).",
  catalogDescriptionLanguageNote:
    "Catalog permission descriptions are in Russian (product default).",
  roleCodeTooltip: "Role code",
  criticalOwnerRole: "Confirm changing owner role permissions",
  criticalOwnerRoleMsg:
    "You are changing the base owner role permissions. This may affect the owner’s access to all critical areas.",
  criticalSelfRole: "Confirm removing a critical role from yourself",
  criticalSelfRoleMsg:
    "You are removing role(s) from yourself: {roles}. You may lose rbac.manage and access to this screen.",
  criticalSelfRbac: "Confirm removing rbac.manage from yourself",
  criticalSelfRbacMsg:
    "You are denying yourself rbac.manage. After saving you may lose access to this screen.",
  tableField: "Field",
  tableBefore: "Before",
  tableAfter: "After",
  btnCreateClinicRole: "Create clinic role",
  modalCreateRoleTitle: "New clinic role",
  labelNewRoleCode: "Role code (latin, unique within clinic)",
  phNewRoleCode: "e.g. reception_lead",
  labelNewRoleName: "Display name",
  phNewRoleName: "e.g. Reception (lead)",
  labelPermissionPreset: "Permission preset (fill list)",
  optPresetNone: "No preset — pick permissions manually",
  presetLabelManager: "Like system role «Manager»",
  presetLabelAdmin: "Like system role «Administrator»",
  presetLabelDoctor: "Like system role «Doctor»",
  labelFillFromRole: "Or copy permissions from role",
  optFillFromRoleNone: "Do not copy",
  hintCreateRolePermissions:
    "Select at least one permission. Presets and copy only fill the list — review and edit before saving.",
  labelCreateRoleNote: "Audit note (optional)",
  phCreateRoleNote: "Why this role is created",
  btnSubmitNewRole: "Create role",
  errCreateRoleCode:
    "Role code: lowercase latin letters, digits, underscores; must start with a letter. System role codes are reserved.",
  errCreateRoleName: "Enter a display name for the role.",
  errCreateRolePerms: "Select at least one permission.",
  btnDeleteClinicRole: "Delete clinic role",
  modalDeleteRoleTitle: "Delete clinic role?",
  modalDeleteRoleBody:
    "Only clinic-specific roles can be removed (not global system roles). If staff are still assigned this role, remove assignments under Staff first.",
  confirmDeleteRole: "Delete",
};

export const rbacRightsPoliciesPageCopy: Record<UiLocale, RbacRightsPoliciesCopy> = {
  ru: RU,
  en: EN,
};

export function getRbacRightsPoliciesCopy(locale: UiLocale): RbacRightsPoliciesCopy {
  return rbacRightsPoliciesPageCopy[locale];
}

export function getRolePresetOptionLabel(code: string, t: RbacRightsPoliciesCopy): string {
  switch (code) {
    case "manager":
      return t.presetLabelManager;
    case "admin":
      return t.presetLabelAdmin;
    case "doctor":
      return t.presetLabelDoctor;
    default:
      return code;
  }
}

const POLICY_LABELS_RU: Record<string, string> = {
  allow_patient_disable_discount_notifications: "Пациент может отключить уведомления о скидках",
  allow_patient_disable_reminders: "Пациент может отключить напоминания",
  allow_patient_disable_all_notifications: "Пациент может отключить все уведомления",
  owner_morning_brief_enabled: "Утренняя сводка владельцу включена",
  morning_brief_send_at_utc: "Время утренней сводки (UTC)",
  owner_telegram_chat_id: "Telegram chat ID владельца",
  ai_supervisor_enabled: "AI Supervisor включен",
  ai_supervisor_send_at_utc: "Время отправки AI Supervisor (UTC)",
  ai_supervisor_recipient_chat_ids: "Получатели AI Supervisor",
};

const POLICY_LABELS_EN: Record<string, string> = {
  allow_patient_disable_discount_notifications: "Patient can disable discount notifications",
  allow_patient_disable_reminders: "Patient can disable reminders",
  allow_patient_disable_all_notifications: "Patient can disable all notifications",
  owner_morning_brief_enabled: "Owner morning brief enabled",
  morning_brief_send_at_utc: "Morning brief time (UTC)",
  owner_telegram_chat_id: "Owner Telegram chat ID",
  ai_supervisor_enabled: "AI Supervisor enabled",
  ai_supervisor_send_at_utc: "AI Supervisor send time (UTC)",
  ai_supervisor_recipient_chat_ids: "AI Supervisor recipients",
};

export function getPolicyFieldLabel(key: string, locale: UiLocale): string {
  const map = locale === "ru" ? POLICY_LABELS_RU : POLICY_LABELS_EN;
  return map[key] ?? key;
}

/** Стили подсказки: светлый фон и хороший контраст (в т.ч. для второго абзаца). */
export const rbacTooltipStyles = {
  tooltip: {
    backgroundColor: "var(--mantine-color-body)",
    color: "var(--mantine-color-text)",
    border: "1px solid var(--mantine-color-default-border)",
    boxShadow: "var(--mantine-shadow-md)",
    maxWidth: 440,
  },
} as const;
