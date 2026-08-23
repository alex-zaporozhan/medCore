# README screenshots

Put PNGs here. The root README lists expected names; it does not yet embed images (add them when the files exist).

| File | Shot | Produced by helper? |
|---|---|---|
| `admin-login.png` | `/admin/login` | yes |
| `admin-dashboard.png` | `/admin` after sign-in | yes |
| `admin-schedule.png` | `/admin/schedule` | yes |
| `admin-omni-chat.png` | `/admin/omni-chat` | yes |
| `admin-tasks.png` | `/admin/tasks` | yes |
| `patient-booking.png` | Patient booking wizard | **manual** (different auth; copy may still be Russian) |

Needs a running API + seeded staff (`documentation/DEMO_CREDENTIALS.md`). Preview-only with no API will fail login.

**Compose UI (port 3010):**

```powershell
cd frontend
$env:README_SCREENSHOTS = "1"
$env:BASE_URL = "http://127.0.0.1:3010"
npx playwright test e2e/readme-screenshots.spec.ts
```

```bash
cd frontend
README_SCREENSHOTS=1 BASE_URL=http://127.0.0.1:3010 npx playwright test e2e/readme-screenshots.spec.ts
```

`BASE_URL` also skips Playwright’s preview webServer (see `frontend/playwright.config.ts`).

**Host preview (4173) + API on 8000:** `npm run build` first, then `README_SCREENSHOTS=1` without `BASE_URL`.

Do not commit live PHI. Demo seeds only. `cmd.exe` uses `set VAR=value` (not `$env:`).
