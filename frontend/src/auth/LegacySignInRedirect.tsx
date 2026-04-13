import { ROUTE_PATHS, patientPublicLoginSearch } from "@/routePaths";
import { Center, Loader } from "@mantine/core";
import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

/**
 * Старый единый `/sign-in?tab=…` → раздельные маршруты. Сохраняет `returnTo` где уместно.
 */
export default function LegacySignInRedirect() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const tab = searchParams.get("tab");
    const returnTo = searchParams.get("returnTo");
    const q = new URLSearchParams();
    if (returnTo) q.set("returnTo", returnTo);

    const search = q.toString() ? `?${q.toString()}` : "";

    if (tab === "founder") {
      navigate({ pathname: ROUTE_PATHS.platform.login, search }, { replace: true });
      return;
    }
    if (tab === "clinic") {
      navigate({ pathname: ROUTE_PATHS.admin.login, search }, { replace: true });
      return;
    }
    navigate(
      {
        pathname: ROUTE_PATHS.other.login,
        search: patientPublicLoginSearch("need-clinic"),
      },
      { replace: true },
    );
  }, [navigate, searchParams]);

  return (
    <Center h="100vh">
      <Loader size="md" />
    </Center>
  );
}
