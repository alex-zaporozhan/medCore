# Audit: EN toggle vs RU chrome (ports 3010 / 5175)

> **Date:** 2026-08-19 (review pass 10 — owner-invite routed) · **Superseded for leftover surfaces:** 2026-08-21 review (this file no longer wins over `I18N_PUBLIC_EN_PLAN.md` for sandbox/legal/founder/PWA).  
> **Roles:** @QA_ARCH · @ARCH · @FRONTEND · @LEAD  
> **Plan:** [`I18N_PUBLIC_EN_PLAN.md`](./I18N_PUBLIC_EN_PLAN.md)  
> **Priority of truth:** `I18N_PUBLIC_EN_PLAN.md` + files on disk. This audit is a snapshot; leftover pass 2026-08-21 closed sandbox/legal/founder chrome.

---

## 0. Verdict

`:3010` and `:5175` are the **same SPA**. The original screenshots compared **`/admin/login` vs `/login`**, not Docker vs Vite.

**Pass 1 of this audit was already stale against the working tree** (Law 12): `/login` and founder login **are** on `auth` keys; `AdminLayout` **had** `labelKey` / `id` but still rendered `group.title` and `item.label` (fields that do not exist). That is the “declared, does not work” class.

**Pass 10:** `/signup/owner-invite` was **dead**. Wired `ROUTE_PATHS.marketing.ownerInviteAccept`. Catalog `useEffect([t])` would refetch and race on locale change — now `[]`.

**Review 2026-08-21:** sandbox/legal/founder ops/PWA chrome on keys; FE catalog overlay; ADR-018 noscript. Task **modal** + **Kanban/create/routing/stream colour** + **`/admin/tasks/:taskId` chrome** on `tasks` keys. Checkout/lead/HTML 5xx copy on dictionaries. Showcase seed adds EN **Sales** stream + ±14-day ops-window tasks (no `Demo window:` prefix on new titles). **Still mixed RU:** other admin families, seed/API catalog without overlay, backend `detail`. Board/stream **custom names** remain API/seed data.

---

## 1. URL matrix (evidence)

| URL | Component | Chrome source | Default EN? |
|-----|-----------|---------------|-------------|
| `/admin/login` | `ClinicSignInPage` | `auth.clinic.*` | yes |
| `/login` | `PublicLoginPage` | `auth.public.*` + staff panel | **yes in code now** |
| `/platform/login` | `PlatformFounderLoginPage` | `auth.founder.*` | yes |
| `/` | `MarketingLandingPage` | `marketing.*` | **yes** (default `en`) |
| `/signup` | `SignupPage` | `marketing.signup.*` + checkout chrome | **yes**; API option names may be RU |
| `/signup/owner-invite` | `PlatformOwnerInviteAcceptPage` | `marketing.invite.*` | **yes** (routed pass 10) |
| `/admin` after login | `AdminLayout` + page | layout: keys; **page** often literals | mixed |
| `/c/:slug/sign-in` | patient | literals | no |

Landing **Sign in** → `ROUTE_PATHS.admin.login`. Patient link stays `/login`:

```159:181:frontend/src/marketing/pages/MarketingLandingPage.tsx
              <Anchor component={Link} to={ROUTE_PATHS.other.login} size="sm" c="dimmed" fw={500}>
                {t("header.patientApp")}
              </Anchor>
              <Button
                component={Link}
                to={ROUTE_PATHS.admin.login}
                variant="subtle"
                color="gray"
                data-testid="landing-staff-sign-in"
              >
                {t("header.signIn")}
              </Button>
              …
              <UiLocaleSwitch />
```

If `/login` still looks Russian with the EN segment selected: `localStorage.ui.locale === "ru"` on **that origin**, or an old Docker `dist`. Origins `:3010` and `:5175` do not share storage.

---

## 2. Locale clock

| Mechanism | Fact |
|-----------|------|
| Default | `fallbackLng: "en"`; empty `ui.locale` → `en` |
| Toggle | `UiLocaleSwitch` on SignInShell, founder header, landing/signup header, admin sidebar (expanded) or Main (collapsed) |
| Storage | `localStorage["ui.locale"]` per origin |
| `document.lang` | `isDocumentLocalePath`: `/admin*`, `/login`, `/`, `/signup`, `/pricing`, `/sandbox`, `/legal/*`, `/platform*`, `/app`, `/c/*`, public `/doctors/` → `ui.locale`. Unmatched public paths → `ru` (`PUBLIC_HTML_LANG`) |
| `index.html` | `lang="en"`, title MedCore, English description |

**Race (real, small):** first HTML paint is EN (`index.html`); JS then sets `document.lang` from `ui.locale` on locale paths. Not a queue. No Celery involvement.

**Not a race:** two APIs (`:8000` host uvicorn vs `:8010` compose) share Postgres; chat messages appear on both UIs. Language is not stored in the API.

---

## 3. Shadow dictionaries (formal ≠ rendered)

JSON **already existed** and tests already asserted EN strings. Wiring lagged.

| Dictionary | Tests | UI before pass 2 | UI after pass 2 |
|------------|-------|------------------|-----------------|
| `auth.public.*` | `i18nDefaultEn` + `PublicLoginPage.test` | page used `t()` already | same |
| `auth.founder.*` | `i18nDefaultEn` | page used `t()` already | same |
| `nav.json` | `i18nDefaultEn` | **layout rendered `.title` / `.label` (undefined)** | `t(groups.id)` / `t(labelKey)` |
| `common` (home, logout, clinics, spotlight) | yes | layout mixed | layout chrome on `tc()` |
| `feed.json` | `i18nDefaultEn` + dashboard unit + e2e | unused / mixed | **wired** (`AdminDashboardPage`) |
| `reports.json` | `i18nDefaultEn` | unused literals | **wired** (`AdminReportsPage`, `AdminAiReportsPage`) |
| `chat.json` omni | `i18nDefaultEn` + e2e EN | ContextBar + inbox mixed; composer RU | **wired** inbox/composer/analytics; patient/staff chat bodies still mixed |

Roadmap R4 (“founder form stays RU”) and A12 (“no Cyrillic in admin chrome”) **contradicted the tree**. Founder **login** is EN keys; founder **ops pages** after login are still RU. A12: dictionaries yes; many pages and (until pass 2) layout render no.

---

## 4. Design / shell (A1 vs reality)

A1 spec: switcher in **AppShell header** after `ClinicSelector`.

**Fact:** `AdminLayout` has **no** `AppShell.Header`. `ClinicSelector` is used on schedule/waitlist breadcrumbs, not in the shell. The sidebar uses a raw `Select` (R15: two pickers).

**Pass 7 placement:** one `UiLocaleSwitch` — sidebar footer when expanded (260px fits SegmentedControl); Main top-right only when collapsed. Omni expanded no longer steals a content row. Founder header next to logout. Navbar Home/Logout stay. Deviation from A1 “header after ClinicSelector”; intent (locale always reachable, including collapsed) holds.

---

## 5. E2E vs UI (tests that were already lying)

| Spec | Asserts | Current UI |
|------|---------|------------|
| `smoke-routes` `/admin/login` | `clinic staff sign-in` | matches |
| `smoke-routes` `/login` | heading `/^Sign in$/` | matches **if** `ui.locale=en` |
| `smoke-routes` `/platform/login` | `platform founder` | matches keys |
| `smoke-routes` `/` | EN hero `The operating system…` | matches `marketing.hero.title` |
| `smoke-public` | Patient app + EN heading | matches |
| `patient-entry-sign-in` | «Вход пациента» | patient PWA — out of this wave |
| `admin-omni-chat` | EN chrome (`Omni-chat — work only`, Claim, Emoji, Mode, Conversation messages) | matches pass 7; seed names stay RU |

Phase 4 e2e updated in the same change as landing copy. Pass 1 plan said e2e still looks for «Войти» on `/login` — **false** for `smoke-routes`.

---

## 6. Remaining RU (inventory for the plan)

### 6.1 Public (Phase 4 — **closed** except API names + sandbox/legal)

- `MarketingLandingPage.tsx` — `marketing` ns; staff Sign in → `/admin/login`
- `SignupPage.tsx` + `PlatformPricingSection` — chrome, overlay, checkout UI on keys
- API `display_name` / option labels — **backend language** (DECLARED-OPEN E-api)
- Sandbox, legal page bodies — still RU
- `frontend/index.html` — `lang="en"`

### 6.2 Admin pages (Phase 3b leftovers)

- Omni inbox/composer/analytics: **closed** this pass (`chat.json` + EN e2e)
- Tasks / finance bodies — some chrome on keys; grep remaining literals
- Feed + reports chrome: **closed** pass 3

### 6.3 Patient / founder ops

- `/app`, `/c/:slug` — Phase P
- `/platform/dashboard` etc. — **shell** EN keys + locale switch; **page bodies** still RU (Phase F)

### 6.4 Law 20

Layout clinic errors used to mention a closed `docs/` tree. Pass 2 uses `common.clinics.loadErrorBody` (README only).

---

## 7. Review of pass-1 artifacts (what was wrong)

| ID | Class | Issue | Fix |
|----|-------|-------|-----|
| R1 | 🔴 | Audit claimed `PublicLoginPage` hardcoded RU | File already used `auth.public.*` |
| R2 | 🔴 | Plan Phase 2 = new `marketing` ns for `/login` | Would **duplicate** `auth.public`. Ns `marketing` only for landing/signup |
| R3 | 🔴 | `AdminLayout` `labelKey` unused at render | Wired `t()` (pass 2) |
| R4 | 🟠 | Switcher only in collapsed-hidden navbar | Moved to Main |
| R5 | 🟠 | A1 “after ClinicSelector in header” | No header; documented deviation |
| R6 | 🟠 | `html lang` forced `ru` on `/login` | `isDocumentLocalePath` |
| R7 | 🟠 | OSS §0 still “admin chrome/nav closed A12” | Corrected |
| R8 | 🟡 | README: `/login` chrome is English | Nuanced: login **routes** EN; landing/PWA RU; admin **pages** mixed |
| R9 | 🟡 | PRODUCT_OVERVIEW: switcher on admin header | Header does not exist; switcher sidebar XOR Main |
| R16 | 🔴 | Omni e2e asserted RU chrome while default locale is `en`; `canClaim` unused; messages aria frozen RU at module load | Wired `chat.json`, Claim retry, `adminChatMessagesRegion()`, e2e EN |
| R10 | 🟡 | E2E list in plan was wrong | §5 above |
| R11 | 🟡 | Founder “stays RU” | Login EN; ops RU |
| R12 | 🟢 | URL `/login` vs `/admin/login` | Still the original user confusion |
| R13 | 🟢 | Queues/Celery | N/A for i18n |
| R14 | 🟡 | Phase 3b unbounded | First leftover = dashboard/`feed.json` |
| R15 | 🟡 | Completeness ledger missing in plan | Added |

Pass 1 was useful for the URL illusion. It was **not** a complete inventory of the tree.
