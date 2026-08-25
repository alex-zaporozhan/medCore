import { describe, expect, it } from "vitest";

import { ApiErrorWithCode } from "@/api/client";
import { omniFileUploadErrorMessage } from "../omniUploadErrors";

const t = ((key: string) => key) as Parameters<typeof omniFileUploadErrorMessage>[1];

describe("omniFileUploadErrorMessage", () => {
  it("maps omni upload codes to chat error keys", () => {
    expect(omniFileUploadErrorMessage(new ApiErrorWithCode("x", "omni_file_type_denied"), t)).toBe(
      "errors.fileTypeDenied",
    );
    expect(omniFileUploadErrorMessage(new ApiErrorWithCode("x", "omni_file_empty"), t)).toBe("errors.fileEmpty");
    expect(omniFileUploadErrorMessage(new ApiErrorWithCode("x", "omni_file_too_large"), t)).toBe(
      "errors.fileTooLarge",
    );
    expect(omniFileUploadErrorMessage(new ApiErrorWithCode("x", "omni_svg_forbidden"), t)).toBe(
      "errors.fileSvgForbidden",
    );
  });

  it("returns null for unrelated errors", () => {
    expect(omniFileUploadErrorMessage(new ApiErrorWithCode("x", "omni_chat_already_claimed"), t)).toBeNull();
    expect(omniFileUploadErrorMessage(new Error("network"), t)).toBeNull();
  });
});
