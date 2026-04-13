import { ROUTE_PATHS } from "@/routePaths";
import { Navigate } from "react-router-dom";

/**
 * Единая витрина с согласиями и оплатой — на `/signup`. Старый URL `/pricing` сохраняем редиректом.
 */
export default function PricingPage() {
  return <Navigate to={ROUTE_PATHS.marketing.signup} replace />;
}
