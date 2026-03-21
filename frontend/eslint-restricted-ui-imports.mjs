/**
 * Единый список для `no-restricted-imports` (техпаспорт §7 — параллельный UI-kit без эпика).
 * Используется в `eslint.config.mjs` для `src/**` и `src/admin/**` (+ Drawer в админке).
 */

const PARALLEL_UI_KIT_MESSAGE =
  "TECH_PASSPORT §7: replacing Mantine with another UI kit requires an epic and rollback plan (ROLE_FRONTEND).";

/** Пакеты второго UI-стека рядом с Mantine — только по эпику. */
export const TECH_PASSPORT_PARALLEL_UI_KIT_PATHS = [
  { name: "antd", message: PARALLEL_UI_KIT_MESSAGE },
  { name: "@chakra-ui/react", message: PARALLEL_UI_KIT_MESSAGE },
  { name: "@mui/material", message: PARALLEL_UI_KIT_MESSAGE },
  { name: "@mui/system", message: PARALLEL_UI_KIT_MESSAGE },
  { name: "react-bootstrap", message: PARALLEL_UI_KIT_MESSAGE },
  { name: "@headlessui/react", message: PARALLEL_UI_KIT_MESSAGE },
  { name: "@nextui-org/react", message: PARALLEL_UI_KIT_MESSAGE },
  { name: "primereact", message: PARALLEL_UI_KIT_MESSAGE },
];

export const TECH_PASSPORT_ADMIN_MANTINE_DRAWER_PATH = {
  name: "@mantine/core",
  importNames: ["Drawer"],
  message: "Use AdminDrawer from @/shared/ui instead of Mantine Drawer (TECH_PASSPORT §6).",
};
