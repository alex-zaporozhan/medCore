# Plan: public EN + leftover admin pages (approve remaining phases)

> **Status:** Phase 4 **done**. Leftover pass + review (2026-08-21): sandbox/legal (with switcher), founder ops (`FounderQueryError`), finance labels, **live** task modal (`TaskDetailsView`), catalog FE overlay, HTML 4xx/5xx i18n, ADR-018 noscript.  
> **Audit:** [`I18N_SURFACE_AUDIT_2026-08-19.md`](./I18N_SURFACE_AUDIT_2026-08-19.md)  
> **Do not** restart A0–A12. Do **not** add a second dictionary for `/login`.

---

## 0. Goal A → B

**A (historical):** GitHub README is English; staff/founder **login routes** are on `auth` keys; landing was RU; `/login` vs `/admin/login` confused the demo; admin **pages** mixed RU literals with EN dictionaries.

**B remaining after Phase 4 + patient PWA + leftover pass (2026-08-21):**

Other admin drawers beyond tasks/finance chrome (CRM tables, settings sub-screens) · backend `detail` language · ₽ / +7 · `docs/` translation · git commit/push (human, Law 40).

**Already B:** `/login` + `/platform/login` on `auth.*`; admin nav + switcher; feed/reports + omni inbox/composer; landing **Sign in** → `/admin/login`; landing body + signup chrome + checkout overlay/chrome on `marketing`; **`/signup/owner-invite` in `App.tsx`**; `index.html` `lang="en"` + `<noscript>` hero; `isDocumentLocalePath` includes `/`, `/signup`, `/signup/owner-invite`, `/pricing`, `/sandbox`, `/legal/*`, `/platform/*`, `/app`, `/c/*`, public doctor URLs. Patient PWA chrome on `patient` ns. Showcase seed overlays catalog `display_name`; **FE entitlement overlay** on known keys. Showcase **±14-day EN demo window** (`showcase_en_demo_window`) is seed, not Alembic. Founder ops (dashboard / queue / leads / MFA / TOTP) on `founder` ns. Finance page chrome on `money.finance`. Task **modal + Kanban/create/routing/stream colour + `/admin/tasks/:taskId` chrome** on `tasks` keys. HTML 4xx/401 gateway copy on `common.errors`.

---

## 1. Architecture (locked)

| Decision | Value |
|---|---|
| Login copy | **`auth` ns only**. No `marketing` keys for `/login`. |
| Landing / signup | ns `marketing` — registered in `index.ts` + `i18next.d.ts`. |
| Nav | Existing `nav.json`. Layout uses `id` + `labelKey` + `t()`. |
| One switcher | `UiLocaleSwitch`. Admin: sidebar XOR Main. Founder: header. Landing/signup: header `Group` last item; wrap at 360. |
| No language detector | Unchanged. |
| Region | ₽ / YooKassa stay region. |
| Docker | `:3010` needs `docker compose build frontend` after JS changes. |

---

## 2. Completeness ledger (spot-check)

| # | Claim | State | Owner | Cost if skipped |
|---|--------|-------|-------|-----------------|
| 1 | `/login` EN at default | DECIDED | — | — |
| 2 | Nav labels EN | DECIDED | — | — |
| 3 | Switcher after login | DECIDED | — | — |
| 4 | `html lang` on login + `/` + `/signup` + `/signup/owner-invite` + `/pricing` + `/sandbox` + `/legal/*` + public doctor URLs | DECIDED — `isDocumentLocalePath` | — | — |
| 5 | Landing CTA → `/admin/login` | DECIDED | — | — |
| 6 | Landing body EN | DECIDED — `marketing` ns + page `t()` + e2e | — | — |
| 6b | Signup checkout chrome EN | DECIDED — `PlatformPricingSection` + overlay keys | — | API names still catalog language |
| 6c | `/signup/owner-invite` | DECIDED — routed + `marketing.invite` | — | email after pay was a blank SPA |
| 7 | Feed page EN | DECIDED | — | — |
| 8 | `index.html` EN | DECIDED — `lang="en"`, MedCore title/description, `<noscript>` hero | — | SPA `#root` until JS; TECH not claimed |
| 9 | Patient PWA | DECIDED — `patient` ns including loyalty/forms/feed/success; `/app` `/c/` in `isDocumentLocalePath` | — | API form/template labels; signature default props |
| 10 | SSG / curl-without-JS | DECIDED — ADR-018: SPA + noscript shell; TECH still not claimed | @ARCH | full SSG of marketing site |

@LEAD spot-check: (6) `MarketingLandingPage` `t("hero.title")`; (8) `frontend/index.html`; (4) `isDocumentLocalePath("/")`.

---

## 3. Phases

### Phase 1 — Landing staff CTA — **done**

### Phase 3-feed / A8 / omni chrome — **done**

### Phase 4 — Landing + HTML shell — **done** (APPROVED)

- `marketing` ns: landing + signup chrome + enterprise lead modal
- Switcher last in landing (and signup) header `Group`; wrap allowed
- `index.html` `lang="en"`, MedCore title/description
- `/` and `/signup` (and `/pricing` redirect) in `isDocumentLocalePath`
- `smoke-routes` + `smoke-public` EN in the same change
- **Review pass 10:** `ROUTE_PATHS.marketing.ownerInviteAccept` + `App.tsx` route (page existed, route did not). Catalog fetch no longer depends on `t` (locale switch does not reset checkout). Empty `payment_url` shows an error. Turnstile load error on keys.

**SEO:** TECH gate **not** claimed. Rendering: ADR-018 (SPA + noscript), not SSG.

### Phase 5 — remaining (do not skip silently)

| ID | Item | State | Next |
|----|------|-------|------|
| P | Patient PWA `/app`, `/c/:slug` | DECIDED (2026-08-20) | ns `patient` including loyalty/forms/feed/success; seed EN names + 5×10 staff huddles |
| F | Founder ops bodies after login | DECIDED | `founder` ns: dashboard, provision queue, leads, MFA, TOTP modal |
| S | `/sandbox` + legal placeholders | DECIDED | `marketing.sandbox` / `marketing.legal` (placeholder, not counsel-approved legal) |
| E-api | Catalog API `display_name` / options | PARTIAL | Seed overlay + **FE** `labelForEntitlementKey`. Alembic rows stay RU until seed. **No backend locale column. Demo EN data is seed (`showcase_en_*` + ±14-day `showcase_en_demo_window`), not Alembic INSERTs.** |
| T | HTML 4xx/5xx in `client.ts` | DECIDED | `common.errors.method_not_allowed` / `html_gateway` / `unauthorized` / `service_unavailable` / `internal_server_error`. Admin 401 is `ApiErrorWithCode`. |
| 3b | Tasks / finance admin bodies | PARTIAL | Finance chrome + cashbox/tx type labels. **Task modal + Kanban/create/routing/stream colour/chat/approval queue + task details page chrome** on `tasks` keys. Other admin families remain one family per PR. |
| SEO | SSG / curl-without-JS | DECIDED as ADR-018 | noscript shell; do not claim TECH |

---

## 4. Explicitly cancelled (pass 1 errors)

- **Cancelled:** new `marketing` ns for `PublicLoginPage`.
- **Cancelled:** “put switcher after ClinicSelector in AppShell.Header” as a hard requirement.
- **Cancelled:** treating A12 as closed for all `admin/pages`.
- **Cancelled:** “e2e still asserts «Вход» on `/login`” as the main e2e risk.

---

## 5. Gates

| Gate | When | Evidence |
|------|------|----------|
| Vitest | Phase 4 | landing heading EN + switcher; `isDocumentLocalePath("/")`; marketing key parity |
| Phase 1 | CTA | href `/admin/login` |
| Phase 3-feed | dashboard | EN chrome |
| Phase 4 | landing | EN + e2e updated together |
| @QA_VISUAL | 4 | header wrap at 360; switcher last in Group |
| @SEO | 4 | title/description/lang; TECH **not** claimed |

---

## 6. Risks

| Risk | Mitigation |
|------|------------|
| Docker old `dist` | rebuild frontend image |
| Two origins / two `ui.locale` | expected |
| Duplicate switcher | one copy per shell |
| Signup catalog still RU | Overlay+chrome closed; **showcase seed** overlays `display_name`; migrate-only DBs stay Alembic language |
| `lang=en` while body RU | closed for `/`, `/signup`, `/pricing`, `/sandbox`, `/legal/*`, patient PWA, founder ops chrome |
| Re-run extras after EN titles | extras counts **RU and EN** Kanban/calendar/feed/promo prefixes so staff calendar is not duplicated |

Queues / booking races: extras calendar overlap on re-seed after EN relabel — **fixed** (dual prefix). Booking slot lock unchanged.

---

## 7. Human approval

Received:

```
I18N_PUBLIC_EN_PLAN: APPROVED
Phases: 4
```
