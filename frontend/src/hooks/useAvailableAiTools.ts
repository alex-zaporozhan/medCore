import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export type AvailableToolDto = {
  tool_id: string;
  label: string;
  description: string;
  required_permissions?: string[] | null;
  allowed_roles?: string[] | null;
};

type AvailableToolsResponse = {
  items: AvailableToolDto[];
};

export function useAvailableAiTools(clinicId: string | null) {
  const query = useQuery({
    queryKey: ["admin-omni-available-tools"],
    queryFn: () => api.get<AvailableToolsResponse>("/v1/admin/omni/available-tools"),
    staleTime: 60_000,
    retry: 0,
    enabled: !!clinicId,
  });

  const tools = useMemo(() => query.data?.items ?? [], [query.data?.items]);
  const toolIds = useMemo(() => new Set(tools.map((t) => t.tool_id)), [tools]);

  const hasAll = useMemo(() => {
    return (requiredToolIds: string[]) => requiredToolIds.every((id) => toolIds.has(id));
  }, [toolIds]);

  void clinicId;

  return {
    ...query,
    tools,
    toolIds,
    hasAll,
  };
}

