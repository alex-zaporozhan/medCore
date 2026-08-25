# Security

MedCore (this repository) is a multi-tenant clinic OS. Tenant isolation bugs are security bugs.

Report vulnerabilities privately to **Alexandr Zaporojan** (`alexandr.zaporojan@gmail.com`). Do not open a public GitHub issue for credential leaks, auth bypass, or tenant isolation bugs.

Include: affected path or endpoint, a short reproduction, and impact (who can read or change whose data).

Demo logins in `documentation/CREDENTIALS_REFERENCE.md` are for local seeds only. Never reuse them in a real deployment.
