import { Group } from "@mantine/core";
import type { ReactNode } from "react";
import { UiLocaleSwitch } from "@/i18n/UiLocaleSwitch";

/** Public marketing pages without the landing header: switcher last in the row; wrap at 360. */
export function MarketingPublicChrome({ children }: { children: ReactNode }) {
  return (
    <>
      <Group justify="flex-end" wrap="wrap" px="md" py="sm">
        <UiLocaleSwitch />
      </Group>
      {children}
    </>
  );
}
