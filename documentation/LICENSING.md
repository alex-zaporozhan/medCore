# Licensing (plain language)

MedCore uses **[PolyForm Shield 1.0.0](https://polyformproject.org/licenses/shield/1.0.0)**. SPDX in manifests: `LicenseRef-PolyForm-Shield-1.0.0` (Shield is not yet on the official SPDX list).

This is **source-available**, not OSI “Open Source.” The Open Source Definition does not allow a field-of-use restriction. Shield has one: a noncompete, not a noncommercial clause.

## You may

- Read, run, and study the code.
- Modify it for yourself.
- Run it for a clinic **you operate** (you are not selling a competing clinic OS).
- Use it as a reference while building something that is not a practical substitute for this product.

No separate permission and no fee for those uses.

## You may not

- Offer a **competing clinic operating system** or booking SaaS — hosted or on-prem — built from this software, including a reskin or a “practical substitute.”
- Strip the `Required Notice:` / `Licensor Line of Business:` lines.

## Why not MIT or Apache-2.0

Those licenses explicitly allow a third party to copy this repository and sell a competing clinic OS. That is the opposite of why this source is public: **inspect and verify**, not **clone the business**.

## Why not a Noncommercial license

PolyForm Noncommercial and CC-BY-NC would block a paying clinic from running the software at all. The intent is to block a **competitor product**, not to block operational use.

## Same family as LEO

[LEO](https://github.com/alex-zaporozhan/leo) uses Shield for the framework (do not resell the constitution). MedCore uses Shield for the clinic OS (do not resell the product). Decision record: [ADR-017](../docs/adr/ADR-017-source-available-polyform-shield.md).

Commercial license for a competing product, or a question that is not covered here: [LinkedIn](https://www.linkedin.com/in/alex-zaporozhan/) or `alexandr.zaporojan@gmail.com` (mailbox spelling is intentional).
