/**
 * Переиспользуемый слой без доменной логики страниц (техпаспорт §4).
 * Компоненты UI — преимущественно из `./ui`.
 */
export { ErrorBoundary } from "./ErrorBoundary";
export {
  formatQueryError,
  getBookingErrorMessage,
  type BookingErrorCode,
} from "./errors";
export * from "./aiFeatures";
export * from "./uiEvents";
export * from "./crmStageSemantics";
export { EmptyStateHint } from "./emptyStateHint";
export { getCurrentUtm, useUtmTracking } from "./utmTracking";
export type { StoredUtmContext } from "./utmTracking";
export * from "./ui";
