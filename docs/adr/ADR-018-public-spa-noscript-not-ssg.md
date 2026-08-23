# ADR-018: Public marketing remains a SPA; curl-without-JS is the HTML shell

- **Status:** Accepted
- **Date:** 2026-08-21
- **Context:** SEO TECH (`roles/SEO_CANON.md`) asks that `curl` without JavaScript return page content. The product UI is a Vite SPA (`frontend/`). Moving `/admin`, `/app`, and `/platform` onto SSG/SSR would change the architecture (new framework or a prerender farm) without changing clinic operations. Claiming SEO TECH while the body is an empty `#root` would be a false gate.

## Decision

1. **Keep Vite SPA** for the operational product and the current marketing routes (`/`, `/signup`, `/sandbox`, `/legal/*`).
2. **`frontend/index.html`** is the no-JS shell: `lang="en"`, title, description, and a **`<noscript>`** block with the English hero heading and product sentence. That is the honest “curl without JS” surface for this wave.
3. **Do not claim SEO TECH** until a dedicated public-site rendering ADR (SSG/SSR of indexable URLs, 1 cluster = 1 page) is implemented.
4. A future public-site split (separate SSG app or prerender of `/` only) is allowed; it is not this i18n leftover.

## Alternatives rejected

| Option | Why not |
|--------|---------|
| Next.js rewrite of the SPA | Cross-cutting, not required to ship EN chrome |
| Prerender every admin route | Admin is authenticated; crawlers should not index it (`noindex`) |
| Fake TECH pass on empty `#root` | Violates Law 14 |

## Links

`frontend/index.html` · `docs/artifacts/I18N_PUBLIC_EN_PLAN.md`
