import { describe, expect, it } from "vitest";
import type { DrawerProps, MantineTheme, ModalProps } from "@mantine/core";
import {
  ADMIN_NAV_SAFE_MODAL_PROPS,
  ADMIN_SHELL_NAVBAR_OFFSET,
  mergeDrawerStyles,
  mergeModalStyles,
  SHELL_MODAL_CONTENT_STYLE,
  SHELL_MODAL_NAV_INNER_STYLE,
  SHELL_OVERLAY_PROPS,
} from "../shellPanelStyles";

const fakeTheme = {} as MantineTheme;

describe("SHELL_OVERLAY_PROPS", () => {
  it("has stable blur and opacity for shell parity", () => {
    expect(SHELL_OVERLAY_PROPS.blur).toBe(10);
    expect(SHELL_OVERLAY_PROPS.backgroundOpacity).toBe(0.08);
  });

  it("keeps overlay out of the admin navbar column", () => {
    expect(SHELL_OVERLAY_PROPS.style).toMatchObject({ left: ADMIN_SHELL_NAVBAR_OFFSET });
    expect(ADMIN_NAV_SAFE_MODAL_PROPS.lockScroll).toBe(false);
    expect(ADMIN_NAV_SAFE_MODAL_PROPS.trapFocus).toBe(true);
  });
});

describe("mergeModalStyles", () => {
  it("applies glass content when styles undefined", () => {
    const m = mergeModalStyles(undefined);
    expect(typeof m).toBe("object");
    if (typeof m === "object" && m && "content" in m && m.content) {
      expect(m.content).toMatchObject(SHELL_MODAL_CONTENT_STYLE);
    }
    if (typeof m === "object" && m && "inner" in m && m.inner) {
      expect(m.inner).toMatchObject(SHELL_MODAL_NAV_INNER_STYLE);
      expect(m.inner).not.toHaveProperty("paddingLeft");
    }
    if (typeof m === "object" && m && "content" in m && m.content) {
      expect(m.content).toMatchObject({ pointerEvents: "auto" });
    }
  });

  it("merges object styles and preserves base content keys", () => {
    const m = mergeModalStyles({
      content: { minHeight: 200 },
      body: { padding: 12 },
    });
    expect(typeof m).toBe("object");
    if (typeof m === "object" && m && "content" in m && m.content) {
      expect(m.content).toMatchObject({
        ...SHELL_MODAL_CONTENT_STYLE,
        minHeight: 200,
      });
    }
    if (typeof m === "object" && m && "body" in m) {
      expect(m.body).toMatchObject({ padding: 12 });
    }
  });

  it("merges function styles so base glass content is not lost", () => {
    const userStyles = ((_theme: MantineTheme, _props: ModalProps, _ctx: unknown) => ({
      content: { minWidth: 400 },
    })) as unknown as ModalProps["styles"];
    const m = mergeModalStyles(userStyles);
    expect(typeof m).toBe("function");
    const resolved = (m as (t: MantineTheme, p: ModalProps, c: unknown) => Record<string, unknown>)(
      fakeTheme,
      { opened: true, onClose: () => {} } as ModalProps,
      {}
    );
    expect(resolved.content).toMatchObject({
      ...SHELL_MODAL_CONTENT_STYLE,
      minWidth: 400,
    });
  });
});

describe("mergeDrawerStyles", () => {
  it("returns drawer shell when styles undefined", () => {
    const s = mergeDrawerStyles(undefined);
    expect(typeof s).toBe("object");
    if (typeof s === "object" && s && "content" in s && s.content) {
      expect(s.content).toMatchObject({
        backdropFilter: "blur(10px)",
      });
    }
  });

  it("merges body with base drawer styles", () => {
    const s = mergeDrawerStyles({ body: { paddingTop: 0 } });
    expect(typeof s).toBe("object");
    if (typeof s === "object" && s && "body" in s) {
      expect(s.body).toMatchObject({
        flex: 1,
        minHeight: 0,
        overflowY: "auto",
        overscrollBehavior: "contain",
        paddingTop: 0,
      });
    }
  });

  it("merges function styles with base shell", () => {
    const userStyles = ((_theme: MantineTheme, _props: DrawerProps, _ctx: unknown) => ({
      body: { padding: 8 },
    })) as unknown as DrawerProps["styles"];
    const s = mergeDrawerStyles(userStyles);
    expect(typeof s).toBe("function");
    const resolved = (s as (t: MantineTheme, p: DrawerProps, c: unknown) => Record<string, unknown>)(
      fakeTheme,
      { opened: true, onClose: () => {} } as DrawerProps,
      {}
    );
    expect(resolved.body).toMatchObject({
      flex: 1,
      minHeight: 0,
      overflowY: "auto",
      overscrollBehavior: "contain",
      padding: 8,
    });
    expect(resolved.content).toMatchObject({ backdropFilter: "blur(10px)" });
  });
});
