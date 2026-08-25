# ADR-017: Source-available license (PolyForm Shield), not MIT

- **Status:** Accepted
- **Date:** 2026-08-17
- **Context:** The repository is published so others can inspect, run, and verify a multi-tenant modular monolith. The owner does not want a third party to copy the codebase and sell a competing clinic OS (Yclients-class product). MIT/Apache grant that right. OSI “open source” and “keep exclusive commercial rights” cannot both be true.

## Decision

1. SPDX in manifests: **`LicenseRef-PolyForm-Shield-1.0.0`** (`pyproject.toml`, `frontend/package.json`). Human name: PolyForm Shield 1.0.0. Canonical text: [polyformproject.org/licenses/shield/1.0.0](https://polyformproject.org/licenses/shield/1.0.0), stored in root `LICENSE`. Required Notice (verbatim): `Required Notice: Copyright 2026 Alexandr Zaporojan. MedCore (multi-tenant clinic operating system; also known as Dental Booking).`
2. Permitted without a separate commercial deal: download, run, study, personal use, internal use in a clinic you operate (you are not offering a competing product).
3. Not permitted: providing a competing product or practical substitute (hosted or on-prem clinic OS / booking SaaS built from this software).
4. `LICENSE` includes `Required Notice:` and `Licensor Line of Business:` so the discontinued-product loophole does not open a competing clinic OS.
5. Public docs say **source-available**, not OSI Open Source. GitHub hosting is unchanged.

## Alternatives rejected

| Option | Why not |
|--------|---------|
| MIT / Apache-2.0 | Explicitly allows selling a competing SaaS |
| PolyForm Noncommercial | Forbids running the software in a paying clinic (too wide) |
| AGPL / SSPL / BSL / Elastic | Project deny-list for inbound deps; also the wrong shape for this intent |
| FSL (converts to Apache) | Would give competitors OSI rights after the delay; owner wants lasting reservation |

Copyright holder / commercial licensing: **Alexandr Zaporojan** (Moldovan passport spelling; GitHub / LinkedIn handles may still use the `Zaporozhan` transcription). Email mailbox stays `alexandr.zaporojan@gmail.com` (do not “correct” the local-part). Product licensing of competing clinic OS remains a separate contract, not this file.

## Links

`LICENSE` · `README.md` · `docs/artifacts/OSS_PUBLIC_READINESS_PLAN.md`
