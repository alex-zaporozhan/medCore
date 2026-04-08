import { createContext, useContext, useMemo } from "react";
import { Outlet, useParams } from "react-router-dom";

export type PatientEntryValue = {
  /** Публичный slug клиники из `/c/:clinicSlug/…`; `null` вне этого контура. */
  clinicSlug: string | null;
};

const PatientEntryContext = createContext<PatientEntryValue>({ clinicSlug: null });

export function usePatientEntry(): PatientEntryValue {
  return useContext(PatientEntryContext);
}

/**
 * Оборачивает маршруты `/c/:clinicSlug/*` и передаёт slug в контекст для patient auth и соглашений.
 */
export function PatientEntryBoundary() {
  const { clinicSlug: raw } = useParams();
  const value = useMemo<PatientEntryValue>(() => {
    const s = typeof raw === "string" ? raw.trim() : "";
    return { clinicSlug: s ? s : null };
  }, [raw]);
  return (
    <PatientEntryContext.Provider value={value}>
      <Outlet />
    </PatientEntryContext.Provider>
  );
}
