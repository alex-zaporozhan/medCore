# Access rights & policies (RBAC): business guide (English)

This is the **secondary-language companion** to `RBAC_RIGHTS_POLICIES_GUIDE.md`.  
The product UI defaults to **Russian**; use this document for international stakeholders, training in English, or sales enablement.

---

## Where to work in the product

Path: `/admin/rights-policies`

Four areas:

1. **Roles & job profiles** — standard access for a job title  
2. **Staff** — assign roles and optional personal overrides  
3. **System policies** — clinic-wide rules (not per user)  
4. **Audit** — who changed what and when  

---

## Core ideas

### Role

A reusable template for a position (e.g. manager, admin). Everyone with that role gets the same baseline permissions.

### Permission

One concrete allowed action in the product (e.g. view payroll, manage CRM).

### Grant / deny (personal overrides)

- **Grant** — add a permission on top of roles (exceptional “extra access”).  
- **Deny** — block a permission even if a role would normally allow it.

Prefer fixing access through **roles** first; use overrides sparingly.

### Policy

A **clinic-wide** switch or setting (notifications behaviour, owner briefings, etc.), not “this one employee”.

---

## What a “domain” is

**A domain is not your org chart.** In the UI it is a **bucket** derived from the **permission code**: the system takes the first segment before `.` or `_` and groups rows that share it. That keeps long lists manageable.

**What you actually grant** is defined by **each permission row** and its **description**, not by the bucket name. Use domains to **filter** the list; decide **enable/disable** by reading every line you touch.

### Why you may see “View (code prefix)” or “Manage (code prefix)”

Many codes start with `view_…` or `manage_…`. The UI may label that bucket accordingly. **Inside the bucket there can be different business areas** (dashboard, finance, CRM, etc.). Always read the **row description**.

### Typical domain names (indicative)

Exact codes evolve with the product. Orientation:

| System name (typical) | Business meaning |
| --- | --- |
| `view`, `manage` | Grouped by `view_*` / `manage_*` prefixes—mixed areas; read each row. |
| `patients` | Patient personal data and related access. |
| `tasks` | Task workflow permissions (`tasks.*` style codes). |
| `rbac` | Who can change roles and this access screen (`rbac.manage`, etc.). |
| `erp`, `attribution`, `booking`, `ai`, `omni` | Owner reports, marketing ROI, booking AI tools, AI flows, omnichannel inbox—when present in your catalog. |

On the `/admin/rights-policies` screen you will find:

- **Hint language** (Russian / English): Russian is the primary, full layer; English adds a secondary layer for domain hints and the glossary table.
- **Domain filter**: business-oriented title first; the **technical domain key** appears at the end of the row in a quieter style; **hover** for a short explanation.
- **Permission list**: **hover** a row to see the catalog description (same language as in the product catalog).
- **Domain glossary**: a **complete** table for **all** domain groups in your clinic’s catalog, including **all** permission codes in each group; the table is **collapsed by default** and opens on demand.
- **Export**: CSV (UTF-8 with BOM for Excel)—one file for domain metadata and one for the full permission list.

The glossary table lists **only domains that exist in your current catalog**.

---

## Global vs clinic-specific roles and permission presets

- **Global (system) roles** such as owner, manager, admin, doctor ship with the product and are shared semantics across clinics. You **cannot delete** them from the UI; **owner** role permissions are immutable by design.

- **Clinic-specific roles** can be **created** on `/admin/rights-policies`: a unique code (latin, lower case), display name, and a **required explicit permission list**—no hidden defaults. **Presets** optionally fill that list from a matrix bundle (e.g. “like manager”); you should still review every permission before saving. Presets only include permission codes that exist in your database for this release.

- **Deleting** a clinic role is allowed only when **no staff** still have that role; remove assignments under **Staff** first.

- **Staff directory** (`/admin/administrators`) uses the same role codes. If you change **default roles** for a profession category, staff in that category get their **roles replaced** (sync-on-change); personal **grant/deny** overrides on permissions are not removed.

- The API uses **`Accept-Language`** so error messages align with the page language (Russian vs English UI).

---

## Safe workflow

1. Clarify the business need (“who must do what?”).  
2. Change **one role** or **one person** at a time.  
3. Review **Diff before save**.  
4. Save.  
5. Confirm real-world access with the user if possible.  
6. Check **Audit** for the logged change.

---

## Security habits

- Do not remove critical access from yourself without a rollback plan.  
- Prefer least privilege: grant only what the job requires.  
- After sensitive changes, verify **Audit**.

---

## For sales & onboarding positioning

- Transparent access control with an audit trail  
- Separation of **roles**, **exceptions**, and **clinic-wide policies**  
- Domains as a **navigation aid**, with meaning anchored in **per-permission descriptions**

---

## See also

- Full Russian business guide: `RBAC_RIGHTS_POLICIES_GUIDE.md`  
- Canonical permission definitions in code: `src/application/rbac_matrix.py` (for implementers)
