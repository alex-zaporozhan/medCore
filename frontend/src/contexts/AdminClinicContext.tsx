import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useClinics } from "@/hooks";
import type { Clinic, BusinessLexicon } from "@/api/types";

interface AdminClinicContextValue {
  clinics: Clinic[];
  currentClinicId: string | null;
  setCurrentClinicId: (id: string | null) => void;
  isLoading: boolean;
  error: unknown;
  businessLexicon: BusinessLexicon | null;
}

const AdminClinicContext = createContext<AdminClinicContextValue | undefined>(
  undefined
);

interface AdminClinicProviderProps {
  children: ReactNode;
}

export function AdminClinicProvider({ children }: AdminClinicProviderProps) {
  const { data, isLoading, error } = useClinics();
  const [currentClinicId, setCurrentClinicId] = useState<string | null>(null);

  const clinics = data ?? [];

  useEffect(() => {
    if (!clinics.length) return;
    setCurrentClinicId((prev) => prev ?? clinics[0].id);
  }, [clinics]);

  return (
    <AdminClinicContext.Provider
      value={{
        clinics,
        currentClinicId,
        setCurrentClinicId,
        isLoading,
        error,
        businessLexicon:
          (clinics.find((c) => c.id === currentClinicId)?.business_lexicon as BusinessLexicon | undefined) ?? null,
      }}
    >
      {children}
    </AdminClinicContext.Provider>
  );
}

export function useAdminClinic() {
  const ctx = useContext(AdminClinicContext);
  if (!ctx) {
    throw new Error("useAdminClinic must be used within AdminClinicProvider");
  }
  return ctx;
}

export function useBusinessLexicon() {
  const { businessLexicon } = useAdminClinic();
  if (!businessLexicon) {
    return {
      business_type: "stomatology",
      business_type_custom_name: null,
      person_label_singular: "Пациент",
      person_label_plural: "Пациенты",
      staff_label_plural: "Врачи",
      role_display: {},
    } as BusinessLexicon;
  }
  return businessLexicon;
}

