import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface OwnerOmniChannel {
  id: string;
  type: string;
  display_name: string;
  status: string;
  has_credentials: boolean;
}

export interface OwnerOmniChannelsResponse {
  items: OwnerOmniChannel[];
}

export interface CreateOwnerOmniChannelRequest {
  type: string;
  display_name: string;
}

export interface UpdateOwnerOmniChannelRequest {
  display_name?: string;
  status?: string;
}

export interface SetOwnerOmniChannelCredentialsRequest {
  provider_type: string;
  scopes?: string | null;
  payload: string;
}

export function useOwnerOmniChannels() {
  return useQuery({
    queryKey: ["owner-omni-channels"],
    queryFn: () => api.get<OwnerOmniChannelsResponse>("/v1/owner/channels"),
  });
}

export function useCreateOwnerOmniChannel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateOwnerOmniChannelRequest) =>
      api.post<OwnerOmniChannel>("/v1/owner/channels", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["owner-omni-channels"] });
    },
  });
}

export function useUpdateOwnerOmniChannel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string;
      body: UpdateOwnerOmniChannelRequest;
    }) => api.put<OwnerOmniChannel>(`/v1/owner/channels/${id}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["owner-omni-channels"] });
    },
  });
}

export function useSetOwnerOmniChannelCredentials() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string;
      body: SetOwnerOmniChannelCredentialsRequest;
    }) =>
      api.post<void>(`/v1/owner/channels/${id}/credentials`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["owner-omni-channels"] });
    },
  });
}

