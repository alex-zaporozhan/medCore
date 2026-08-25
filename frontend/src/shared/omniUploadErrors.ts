import type { TFunction } from "i18next";

import { ApiErrorWithCode } from "@/api/client";

/** Maps structured omni upload API codes (Q9) to chat i18n keys. */
export function omniFileUploadErrorMessage(err: unknown, t: TFunction<"chat">): string | null {
  if (!(err instanceof ApiErrorWithCode)) return null;
  switch (err.code) {
    case "omni_file_type_denied":
      return t("errors.fileTypeDenied");
    case "omni_file_empty":
      return t("errors.fileEmpty");
    case "omni_file_too_large":
      return t("errors.fileTooLarge");
    case "omni_svg_forbidden":
      return t("errors.fileSvgForbidden");
    default:
      return null;
  }
}
