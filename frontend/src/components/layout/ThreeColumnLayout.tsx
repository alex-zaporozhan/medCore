import { Box, Flex, ScrollArea } from "@mantine/core";
import type { ReactNode } from "react";

type ColumnWidthPreset = "narrow-left" | "equal" | "wide-center";

interface ThreeColumnLayoutProps {
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
  preset?: ColumnWidthPreset;
  fullHeight?: boolean;
}

export function ThreeColumnLayout({
  left,
  center,
  right,
  preset = "wide-center",
  fullHeight = true,
}: ThreeColumnLayoutProps) {
  const heightsStyle = fullHeight ? { height: "100%" } : {};

  const columns =
    preset === "narrow-left"
      ? ["260px", "minmax(0, 1.4fr)", "minmax(0, 1fr)"]
      : preset === "equal"
        ? ["minmax(0, 1fr)", "minmax(0, 1fr)", "minmax(0, 1fr)"]
        : ["280px", "minmax(0, 1.6fr)", "minmax(0, 1.1fr)"];

  return (
    <Flex
      gap="md"
      align="stretch"
      style={{
        ...heightsStyle,
        minHeight: 360,
      }}
    >
      <Box
        style={{
          width: columns[0],
          minWidth: 0,
        }}
      >
        <ScrollArea h="100%" type="scroll">
          {left}
        </ScrollArea>
      </Box>
      <Box
        style={{
          flex: 1,
          minWidth: 0,
        }}
      >
        <ScrollArea h="100%" type="scroll">
          {center}
        </ScrollArea>
      </Box>
      <Box
        style={{
          width: columns[2],
          minWidth: 0,
        }}
      >
        <ScrollArea h="100%" type="scroll">
          {right}
        </ScrollArea>
      </Box>
    </Flex>
  );
}

