import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { useClinics } from "@/hooks";
import type { Clinic, BusinessLexicon } from "@/api/types";
import { getBoundAdminClinicId } from "@/api/client";

interface AdminClinicContextValue {
  clinics: Clinic[];
  /** Clinics shown in admin selector (only JWT-bound clinic when admin is logged in). */
  selectableClinics: Clinic[];
  currentClinicId: string | null;
  /** No-op when admin JWT binds a single clinic (prevents UI/API scope mismatch). */
  setCurrentClinicId: (id: string | null) => void;
  /** True when clinic selection is locked to JWT/storage admin clinic. */
  isClinicScopeLocked: boolean;
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
  const location = useLocation();
  const { data, isLoading, error } = useClinics();
  const [currentClinicId, setCurrentClinicIdState] = useState<string | null>(null);
  const [boundClinicId, setBoundClinicId] = useState<string | null>(null);

  const clinics = data ?? [];
  const isClinicScopeLocked = !!boundClinicId;

  useEffect(() => {
    setBoundClinicId(getBoundAdminClinicId());
  }, [location.pathname, clinics]);

  const selectableClinics = (() => {
    if (!boundClinicId) return clinics;
    const hit = clinics.filter((c) => c.id === boundClinicId);
    if (hit.length) return hit;
    return [
      {
        id: boundClinicId,
        name: "Текущая клиника",
        phone: null,
        email: null,
        address: null,
        workday_start: "09:00",
        workday_end: "18:00",
        slot_duration_minutes: 30,
        prepayment_amount: "0",
      } as Clinic,
    ];
  })();

  useEffect(() => {
    const bound = getBoundAdminClinicId();
    if (bound) {
      setCurrentClinicIdState(bound);
      return;
    }
    if (clinics.length) {
      setCurrentClinicIdState((prev) => prev ?? clinics[0].id);
    }
  }, [clinics, location.pathname]);

  const setCurrentClinicId = useCallback((id: string | null) => {
    const bound = getBoundAdminClinicId();
    if (bound && id !== null && id !== bound) {
      return;
    }
    setCurrentClinicIdState(id);
  }, []);

  return (
    <AdminClinicContext.Provider
      value={{
        clinics,
        selectableClinics,
        currentClinicId,
        setCurrentClinicId,
        isClinicScopeLocked,
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
