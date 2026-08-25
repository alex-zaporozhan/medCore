# README screenshots

PNGs here are embedded from the root `README.md`. Demo seed only — no live PHI.

| File | Shot |
|---|---|
| `admin-schedule.png` | Chair grid |
| `admin-schedule-booking.png` | **New booking** modal |
| `admin-schedule-visit.png` | Visit drawer (not in README) |
| `admin-staff-chat.png` | Team chat with a thread open |
| `admin-staff-chat-group.png` | **New group** modal |
| `admin-omni-chat.png` | Patient inbox + open thread |
| `admin-calendar.png` | Staff month calendar |
| `admin-calendar-event.png` | **New event** modal |
| `admin-tasks.png` | Kanban |
| `admin-patient-chart.png` | Patient card, Overview |

```powershell
cd frontend
$env:README_SCREENSHOTS = "1"
$env:BASE_URL = "http://127.0.0.1:3010"
npx playwright test e2e/readme-screenshots.spec.ts
```

`:3010` is the Compose **built** image. After a frontend layout change, either rebuild that image or capture against Vite (`BASE_URL=http://127.0.0.1:5175` / `5176`) so the PNG matches source.

Demo logins: `documentation/DEMO_CREDENTIALS.md`.
