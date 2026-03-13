# Сборка Docker-образов

## Сборка в РФ (проблемы со связью / зеркала)

Чтобы не упираться в EOF и таймауты при обращении к Docker Hub из РФ:

1. **Зеркало реестра** — укажите registry-mirror в Docker:
   - **Docker Desktop (Windows):** Settings → Docker Engine → в JSON добавьте:
     ```json
     "registry-mirrors": ["https://mirror.gcr.io", "https://dockerhub.timeweb.cloud"]
     ```
     → Apply & Restart.
   - **Linux (daemon.json):**
     ```json
     { "registry-mirrors": ["https://mirror.gcr.io", "https://dockerhub.timeweb.cloud"] }
     ```
     Затем: `sudo systemctl restart docker`.

2. **Один раз подтянуть базовые образы** (пока связь есть или зеркало отвечает):
   ```powershell
   docker pull python:3.11-slim@sha256:4057d02a202f69bfbfe10f65300519f612eb00fc595b8499f77d3cfe
   docker pull node:20-slim@sha256:d8a35d586fad3af7abb6fdb9ba972388395405f4d462da9e4a4ddcde67b5
   ```
   В Dockerfile образы уже закреплены по digest — после подтягивания сборка идёт из кэша без запросов к registry.

3. **Сборка без provenance** (см. ниже) — убирает зависание на «resolving provenance».

## Быстрая сборка без provenance (рекомендуется в РФ / при медленной сети)

Шаг **«resolving provenance for metadata file»** может висеть десятки минут из‑за обращений к внешним сервисам attestation. Чтобы не ждать:

**Вариант 1 — скрипт (надёжно):**
```powershell
.\scripts\build-no-provenance.ps1
```
Собирает `api` и `web` через `buildx --provenance=false` и поднимает стек.

**Вариант 2 — переменная окружения для `docker compose build`:**
```powershell
$env:BUILDX_NO_DEFAULT_ATTESTATIONS = "1"
docker compose build api web
docker compose up -d
```
В части окружений может не сработать; тогда используйте скрипт.

## Когда пересобирать api и web

| Что меняли | Действие |
|------------|----------|
| Только фронт (Next.js, `frontend/`) | Пересобрать только **web**: `docker compose build web && docker compose up -d` |
| Только бэкенд (Python, `backend/`) | Пересобрать только **api**: `docker compose build api && docker compose up -d` |
| Оба / первый запуск / смена зависимостей | Пересобрать оба: `.\scripts\build-no-provenance.ps1` или `docker compose build api web && docker compose up -d` |

Пересборка только одного сервиса быстрее; образ другого берётся из кэша.

## Обычная сборка

```bash
docker compose build api web
docker compose up -d
```
Убедитесь, что в `frontend/` есть `.dockerignore` (исключены `node_modules`, `.next`), иначе контекст будет ~300+ MB и сборка сильно замедлится.
