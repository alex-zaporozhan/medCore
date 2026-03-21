import { Paper, type PaperProps } from "@mantine/core";
import type { PropsWithChildren } from "react";

type AppCardProps = PropsWithChildren<
  PaperProps & {
    padded?: boolean;
  }
>;

export function AppCard({ children, padded = true, ...props }: AppCardProps) {
  return (
    <Paper
      radius="lg"
      shadow="sm"
      withBorder
      p={padded ? "md" : 0}
      style={{
        background: "var(--bg-card)",
        borderColor: "var(--divider)",
        boxShadow: "var(--shadow-card)",
        ...props.style,
      }}
      {...props}
    >
      {children}
    </Paper>
  );
}

