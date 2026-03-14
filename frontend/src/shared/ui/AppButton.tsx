import { Button, type ButtonProps } from "@mantine/core";

type AppButtonProps = ButtonProps;

export function AppButton(props: AppButtonProps) {
  return (
    <Button
      radius="xl"
      size={props.size ?? "md"}
      variant={props.variant ?? "filled"}
      color={props.color ?? "brand"}
      {...props}
    />
  );
}

