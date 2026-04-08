import { createContext, useContext, type ReactNode } from "react";

export type PlatformFounderSessionValue = {
  token: string;
  setToken: (token: string) => void;
  logout: () => void;
};

const PlatformFounderSessionContext = createContext<PlatformFounderSessionValue | null>(null);

export function PlatformFounderSessionProvider({
  value,
  children,
}: {
  value: PlatformFounderSessionValue;
  children: ReactNode;
}) {
  return (
    <PlatformFounderSessionContext.Provider value={value}>{children}</PlatformFounderSessionContext.Provider>
  );
}

export function usePlatformFounderSession(): PlatformFounderSessionValue {
  const v = useContext(PlatformFounderSessionContext);
  if (!v) {
    throw new Error("usePlatformFounderSession: вне PlatformFounderSessionProvider");
  }
  return v;
}
