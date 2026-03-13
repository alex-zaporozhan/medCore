import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Patient } from "@/api/types";

interface PatientCreate {
  phone: string;
  full_name?: string | null;
  email?: string | null;
}

interface PatientUpdate {
  full_name?: string | null;
  email?: string | null;
}

export function useCreatePatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PatientCreate) =>
      api.post<Patient>("/v1/patients", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients"] });
    },
  });
}

export function useUpdatePatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: PatientUpdate }) =>
      api.put<Patient>(`/v1/patients/${id}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients"] });
    },
  });
}
