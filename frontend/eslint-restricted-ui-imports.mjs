/**
 * Список для `no-restricted-imports`: единый UI-стек (Mantine) и оболочка `AdminDrawer`.
 * Политика репозитория: корневой DOCUMENTATION_POLICY; визуальные токены — theme.ts / index.css.
 */

const PARALLEL_UI_KIT_MESSAGE =
  "Do not add a second UI kit alongside Mantine without a planned migration (see repository DOCUMENTATION_POLICY).";

/** Пакеты второго UI-стека рядом с Mantine — только по согласованному изменению архитектуры. */
export const RESTRICTED_PARALLEL_UI_KIT_PATHS = [
  { name: "antd", message: PARALLEL_UI_KIT_MESSAGE },
  { name: "@chakra-ui/react", message: PARALLEL_UI_KIT_MESSAGE },
  { name: "@mui/material", message: PARALLEL_UI_KIT_MESSAGE },
  { name: "@mui/system", message: PARALLEL_UI_KIT_MESSAGE },
  { name: "react-bootstrap", message: PARALLEL_UI_KIT_MESSAGE },
  { name: "@headlessui/react", message: PARALLEL_UI_KIT_MESSAGE },
  { name: "@nextui-org/react", message: PARALLEL_UI_KIT_MESSAGE },
  { name: "primereact", message: PARALLEL_UI_KIT_MESSAGE },
];

export const RESTRICTED_ADMIN_MANTINE_DRAWER_PATH = {
  name: "@mantine/core",
  importNames: ["Drawer"],
  message: "Use AdminDrawer from @/shared/ui instead of raw Mantine Drawer (admin shell — shared/ui).",
};
