import { Anchor, type AnchorProps } from "@mantine/core";
import { useCallback, useMemo } from "react";
import { displayPersonName } from "./personNameFallback";
import { usePersonCard, type PersonKind } from "./PersonCardContext";

export type PersonNameLinkProps = Omit<AnchorProps, "onClick" | "children"> & {
  kind: PersonKind;
  id: string;
  label?: string | null;
};

export function PersonNameLink({ kind, id, label, ...props }: PersonNameLinkProps) {
  const { open } = usePersonCard();
  const text = useMemo(() => displayPersonName(label ?? null, id), [label, id]);
  const onClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      open({ kind, id });
    },
    [open, kind, id]
  );

  return (
    <Anchor
      href="#"
      onClick={onClick}
      underline="hover"
      fw={500}
      c="brand.6"
      {...props}
    >
      {text}
    </Anchor>
  );
}

