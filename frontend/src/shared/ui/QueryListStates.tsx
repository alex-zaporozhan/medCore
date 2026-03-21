import { Alert } from "@mantine/core";
import type { ReactNode } from "react";
import { formatQueryError } from "@/shared/errors";
import { PageSkeleton, type PageSkeletonProps } from "./PageSkeleton";

export interface QueryErrorAlertProps {
  error: unknown;
  title?: string;
}

/** Error state for list/detail queries — §11 NFR (не «красная строка» без контекста). */
export function QueryErrorAlert({ error, title = "Не удалось загрузить данные" }: QueryErrorAlertProps) {
  return (
    <Alert color="red" title={title} variant="light">
      {formatQueryError(error)}
    </Alert>
  );
}

export interface QueryListStatesProps {
  isLoading: boolean;
  isError: boolean;
  error?: unknown;
  isEmpty: boolean;
  empty: ReactNode;
  children: ReactNode;
  loading?: ReactNode;
  /** Passed to `PageSkeleton` when `loading` not set */
  skeleton?: Pick<PageSkeletonProps, "variant" | "rows">;
  errorTitle?: string;
}

/**
 * Четыре состояния списка: Loading / Error / Empty / Success (ARCHITECTURE_EXCELLENCE_PASSPORT §11).
 */
export function QueryListStates({
  isLoading,
  isError,
  error,
  isEmpty,
  empty,
  children,
  loading,
  skeleton = { variant: "table", rows: 8 },
  errorTitle,
}: QueryListStatesProps) {
  if (isLoading) {
    return <>{loading ?? <PageSkeleton variant={skeleton.variant} rows={skeleton.rows} />}</>;
  }
  if (isError) {
    return <QueryErrorAlert error={error} title={errorTitle} />;
  }
  if (isEmpty) {
    return <>{empty}</>;
  }
  return <>{children}</>;
}
