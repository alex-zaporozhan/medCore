import i18n, { tNs } from "@/i18n";

/** API/FE role codes that are not the `directory.doctorDrawer.roles.*` key. */
const SPECIALIST_ROLE_TO_DIRECTORY: Record<string, string> = {
  nurse: "nurse",
  therapist: "therapist",
};

function firstString(doctor: object, keys: string[]): string {
  const rec = doctor as Record<string, unknown>;
  for (const key of keys) {
    const value = rec[key];
    if (typeof value === "string") return value.trim();
  }
  return "";
}

/**
 * i18n.t (not a hook) — never render doctor.display_role.
 * Doctor DTO fields: specialist_role, specialist_role_custom_name.
 */
export function doctorRoleLabel(doctor: object): string {
  const role = firstString(doctor, ["specialist_role"]);
  const custom = firstString(doctor, ["specialist_role_custom_name"]);
  if (role === "other" && custom) return custom;
  if (role && role !== "other") {
    const directoryRole = SPECIALIST_ROLE_TO_DIRECTORY[role] ?? role;
    const key = `doctorDrawer.roles.${directoryRole}`;
    // exists() brands the key; typed i18n.t(key, { ns }) then fails — use tNs.
    if (i18n.exists(key, { ns: "directory" })) {
      return tNs("directory", key);
    }
  }
  return tNs("schedule", "specialist");
}
