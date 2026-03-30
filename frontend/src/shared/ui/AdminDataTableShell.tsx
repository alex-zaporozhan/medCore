import { Card, type TableProps } from "@mantine/core";
import type { ReactNode } from "react";

/** Filters / bulk actions row — DGN-P0-02, `index.css` `.data-toolbar-card`. */
export function AdminDataTableToolbar({ children }: { children: ReactNode }) {
  return (
    <Card withBorder p="sm" className="data-toolbar-card">
      {children}
    </Card>
  );
}

/** Table host — DGN-P0-02, `.data-table-card`. */
export function AdminDataTableSurface({ children }: { children: ReactNode }) {
  return (
    <Card withBorder p="sm" className="data-table-card">
      {children}
    </Card>
  );
}

/** Default props for ERP-style admin tables (tabular-nums come from global `Table` / CSS). */
export const ADMIN_TABLE_PROPS: Pick<TableProps, "withRowBorders" | "highlightOnHover" | "verticalSpacing"> = {
  withRowBorders: true,
  highlightOnHover: true,
  verticalSpacing: "sm",
};

export const ADMIN_TABLE_PROPS_COMPACT: Pick<
  TableProps,
  "withRowBorders" | "highlightOnHover" | "verticalSpacing"
> = {
  withRowBorders: true,
  highlightOnHover: true,
  verticalSpacing: "xs",
};
