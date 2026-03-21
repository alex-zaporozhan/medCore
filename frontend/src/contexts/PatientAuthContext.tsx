import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import { API_STORAGE_KEYS } from "@/api/client";

const TOKEN_KEY = API_STORAGE_KEYS.patientToken;
const PATIENT_ID_KEY = API_STORAGE_KEYS.patientId;

interface PatientAuthState {
  accessToken: string | null;
  patientId: string | null;
}

interface PatientAuthContextValue extends PatientAuthState {
  login: (token: string, patientId: string) => void;
  logout: () => void;
}

const PatientAuthContext = createContext<PatientAuthContextValue | null>(null);

function readStored(): PatientAuthState {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const patientId = localStorage.getItem(PATIENT_ID_KEY);
    return {
      accessToken: token,
      patientId: patientId,
    };
  } catch {
    return { accessToken: null, patientId: null };
  }
}

export function PatientAuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<PatientAuthState>(readStored);

  const login = useCallback((token: string, patientId: string) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(PATIENT_ID_KEY, patientId);
    setState({ accessToken: token, patientId });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(PATIENT_ID_KEY);
    setState({ accessToken: null, patientId: null });
  }, []);

  const value = useMemo<PatientAuthContextValue>(
    () => ({
      ...state,
      login,
      logout,
    }),
    [state.accessToken, state.patientId, login, logout]
  );

  return (
    <PatientAuthContext.Provider value={value}>
      {children}
    </PatientAuthContext.Provider>
  );
}

export function usePatientAuth(): PatientAuthContextValue {
  const ctx = useContext(PatientAuthContext);
  if (!ctx) {
    throw new Error("usePatientAuth must be used within PatientAuthProvider");
  }
  return ctx;
}
