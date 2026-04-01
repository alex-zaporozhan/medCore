import { createContext, useCallback, useContext, useMemo, useState } from "react";

export type PersonKind = "staff" | "doctor" | "patient";

export type PersonCardTarget = {
  kind: PersonKind;
  id: string;
};

export type PersonCardApi = {
  open: (t: PersonCardTarget) => void;
  close: () => void;
  target: PersonCardTarget | null;
};

const Ctx = createContext<PersonCardApi | null>(null);

export function PersonCardProvider({ children }: { children: React.ReactNode }) {
  const [target, setTarget] = useState<PersonCardTarget | null>(null);
  const open = useCallback((t: PersonCardTarget) => setTarget(t), []);
  const close = useCallback(() => setTarget(null), []);
  const value = useMemo<PersonCardApi>(() => ({ open, close, target }), [open, close, target]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePersonCard(): PersonCardApi {
  const v = useContext(Ctx);
  if (!v) throw new Error("usePersonCard must be used within PersonCardProvider");
  return v;
}

