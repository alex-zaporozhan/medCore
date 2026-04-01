# LEAD_CICD_SUPPLY_CHAIN_GATES — security-gates для CI/CD и Docker Hub

> **Роль:** @LEAD  
> **Цель:** закрыть пробелы supply-chain security в цепочке `source -> CI -> container image -> Docker Hub -> deploy`.  
> **Статус:** обязательный operational/security artifact для релизного решения `GO / NO-GO`.

---

## 1) Scope и принцип

Этот документ дополняет функциональные и интеграционные gate-артефакты и фокусируется только на:

1. безопасности пайплайнов CI/CD,
2. безопасности артефактов контейнеров,
3. безопасности registry (Docker Hub),
4. доказуемости происхождения release image.

Принцип: **“no trust by default”** — образ без скана/подписи/provenance не может попасть в prod.

---

## 2) L1/L2/L3 для supply-chain

| Уровень | Пример | Политика |
|--------|--------|----------|
| L1 | Неполный метаданный label образа | исправление в спринте |
| L2 | Пропущен один из quality/security checks в non-prod | release только с waiver и датой фикса |
| L3 | Образ без подписи/provenance, критичные CVE, deploy по mutable tag | безусловный `NO-GO` |

---

## 3) Gate matrix (обязательные проверки)

| Gate ID | Контур | Обязательные проверки | Evidence | Verdict rule |
|---------|--------|------------------------|----------|--------------|
| S1 | PR security gates | `ruff`/tests/build + dependency scan + secret scan | CI run URL + отчёты | `NO-GO`, если любой critical finding |
| S2 | Build reproducibility | сборка backend/frontend образов по фиксированному commit SHA | build log + image digest | `NO-GO`, если digest не зафиксирован |
| S3 | Image scanning | scan готовых образов (Trivy/Grype) + fail на `CRITICAL/HIGH` по политике | scan report artifact | `NO-GO`, если policy нарушена |
| S4 | SBOM gate | SBOM для каждого release image (backend/frontend), хранение как artifact | SBOM files + link | `NO-GO`, если SBOM отсутствует |
| S5 | Signature gate | подпись release image и проверка подписи на этапе deploy | sign/verify logs | `NO-GO`, если verify не проходит |
| S6 | Provenance gate | attestation/provenance: источник, commit, workflow, build-time | provenance artifact | `NO-GO`, если provenance отсутствует |
| S7 | Immutable deploy gate | deploy только по `digest`/`GIT_SHA`; `latest` запрещен для prod | deploy manifest/log | `NO-GO`, если prod использует mutable tag |
| S8 | Docker Hub access gate | least-privilege robot tokens, ротация, ограничение push source | access policy doc + audit log | `NO-GO`, если нет scoped credentials |
| S9 | Environment protection | protected environments, required reviewers, manual approval prod | repo settings evidence | `NO-GO`, если защита окружения не включена |
| S10 | Action hardening | GitHub Actions pinned by commit SHA, запрет “floating” версий | workflow diff/report | `NO-GO`, если критичные actions не pinned |

---

## 4) Docker Hub security baseline (обязательно)

1. Отдельные robot credentials для CI (не персональные).
2. Права push только для release workflow.
3. Ротация токенов по регламенту (например, раз в 30-60 дней).
4. Обязательные immutable теги: `GIT_SHA`; веточные теги только вспомогательные.
5. `latest` не используется для prod deploy.
6. Для инцидентов: процедура revoke/rotate с RTO <= 60 минут.

---

## 5) CI/CD hardening baseline (обязательно)

1. Разделение workflow:
   - `pull_request`: test/lint/security gates,
   - `push main`/release: build + scan + sign + provenance + publish.
2. Secrets:
   - долгоживущие секреты минимизировать,
   - предпочтительно OIDC/short-lived credentials, где возможно.
3. Environments:
   - staging/prod как защищённые окружения,
   - required reviewers для prod.
4. Supply-chain policy as code:
   - security thresholds и release blockers выражены явно в workflow.

---

## 6) Release checklist (операционный)

Перед prod релизом должны быть заполнены и подтверждены:

1. PR gates пройдены (`S1`).
2. Image digests зафиксированы (`S2`).
3. Scan reports чистые по policy (`S3`).
4. SBOM приложен к release (`S4`).
5. Signature/verify успешны (`S5`).
6. Provenance artifact приложен (`S6`).
7. Deploy выполняется по digest/sha (`S7`).
8. Docker Hub credentials валидны и scoped (`S8`).
9. Protected env + approvals задействованы (`S9`).
10. Workflows pinned (`S10`).

Любой незакрытый `S3/S5/S6/S7` = автоматический `NO-GO`.

---

## 7) Mandatory workflow blueprint (без “минимальной версии”)

Ниже — обязательный порядок job’ов. Любая попытка “срезать углы” (пропуск job, ручной пуш образа, деплой по `latest`) считается нарушением release policy.

### 7.1 PR workflow (обязательный)

1. `backend-quality`
   - `ruff` -> `pytest` -> (опц.) `mypy`
2. `frontend-quality`
   - `npm ci` -> `npm run build` -> `npm run test`
3. `security-pr`
   - dependency scan + secret scan + policy check
4. `pr-gate`
   - агрегатор статусов; merge запрещён, если любой upstream job failed/skipped

### 7.2 Main/release workflow (обязательный)

1. `preflight`
   - verify branch/ref, commit SHA, required metadata
2. `build-images`
   - build backend/frontend, publish только в internal step outputs (не в prod tag сразу)
3. `scan-images`
   - Trivy/Grype scan на собранные образы
4. `generate-sbom`
   - SBOM для каждого image
5. `sign-images`
   - подпись image digest
6. `provenance-attest`
   - provenance/attestation artifact
7. `publish-registry`
   - push в Docker Hub по immutable тегам (`GIT_SHA`, optional `main`)
8. `staging-deploy`
   - deploy по digest + smoke
9. `prod-approval`
   - manual approval в protected environment
10. `prod-deploy`
   - deploy по digest + post-deploy smoke + evidence snapshot

### 7.3 Жёсткие anti-bypass rules

1. Запрещён ручной push образов в release namespace вне CI workflow.
2. Запрещён prod deploy по mutable тегам (`latest`, branch-only).
3. `publish-registry` не может стартовать, если неуспешны `scan-images`, `generate-sbom`, `sign-images`, `provenance-attest`.
4. `prod-deploy` не может стартовать без `prod-approval` и успешного `staging-deploy`.
5. Waiver допускается только для L2 и только с подписью @LEAD + @OPS и датой закрытия.

### 7.4 Minimal implementation запрет

Любая реализация, где присутствуют только build+push без `scan+sbom+sign+provenance+digest-deploy`, считается **не соответствующей** этому документу и получает автоматический `NO-GO`.

---

## 8) Ownership (RACI)

- **A:** @LEAD (вердикт и политика блокеров)
- **R:** @DEV + @OPS (реализация в workflow/deploy)
- **R:** @QA_ARCH (валидация evidence, контроль policy)
- **C:** @ARCH (архитектурные компромиссы и безопасность supply-chain)

---

## 9) Связанные артефакты

- `QA_ARCH_85_PLUS_ROADMAP.md`
- `QA_ARCH_85_PLUS_8W_EXECUTION_TRACKER.md`
- `LEAD_INTEGRATION_GATES.md`
- `LEAD_DB_CACHE_AUDIT.md`

---

## 10) Definition of Compliance (DoC) — что считается соответствием

### 10.1. Compliance verdict levels

| Вердикт | Условие | Решение по релизу |
|--------|---------|-------------------|
| C0 (Non-compliant) | Есть хотя бы один незакрытый `S3/S5/S6/S7` или нарушены anti-bypass rules | `NO-GO` |
| C1 (Conditionally compliant) | Критичных блокеров нет, но есть L2-отклонения с утверждённым waiver | `GO-WAIVER` |
| C2 (Compliant) | Все обязательные gates пройдены, evidence полный, отклонений нет | `GO` |
| C3 (Hardened) | C2 + подтверждённый тренд стабильности (>= 2 релизных цикла без критичных отклонений) | `GO` + рекомендован как baseline |

### 10.2. Обязательный набор evidence для статуса C2/C3

1. CI run URL с зелёными `S1`-job’ами.
2. Image digests для backend/frontend (immutable references).
3. Scan reports (container/dependency/secrets) с verdict по policy.
4. SBOM artifacts для каждого релизного образа.
5. Signature + verify logs.
6. Provenance/attestation artifacts.
7. Deploy evidence по digest (staging + prod).
8. Approval evidence из protected environment.
9. Action hardening evidence (critical actions pinned by SHA).
10. Docker Hub access policy snapshot (scoped creds + дата ротации).

Если хотя бы один пункт отсутствует, статус автоматически понижается до `C0`.

### 10.3. Что считается нарушением (non-compliance patterns)

1. Build+push без `scan+sbom+sign+provenance`.
2. Prod deploy по `latest` или branch-only tag.
3. Ручной push release image вне CI.
4. Отключение/пропуск security gates без формального waiver.
5. Использование непинованных критичных GitHub Actions.
6. Отсутствие manual approval для prod environment.

Каждый такой случай фиксируется как audit finding с owner и сроком устранения.

### 10.4. Waiver policy (только для L2)

Waiver допустим только если одновременно:

1. Подписан `@LEAD` и `@OPS`.
2. Есть конкретный compensating control на текущий релиз.
3. Есть дата закрытия (не позднее следующего релизного цикла).
4. Waiver отражён в release evidence pack.

Waiver для L3 не допускается.

---

## 11) Release Compliance Report (шаблон на каждый релиз)

### 11.1. Паспорт релиза

| Поле | Значение |
|------|----------|
| Release ID |  |
| Дата/время |  |
| Environment | staging / prod |
| Commit SHA |  |
| Backend image digest |  |
| Frontend image digest |  |
| Decision owners | @LEAD / @OPS / @QA_ARCH |

### 11.2. Gate status (S1..S10)

| Gate | Статус (PASS/FAIL/WAIVER) | Evidence link | Комментарий |
|------|----------------------------|---------------|-------------|
| S1 PR security gates |  |  |  |
| S2 Build reproducibility |  |  |  |
| S3 Image scanning |  |  |  |
| S4 SBOM gate |  |  |  |
| S5 Signature gate |  |  |  |
| S6 Provenance gate |  |  |  |
| S7 Immutable deploy gate |  |  |  |
| S8 Docker Hub access gate |  |  |  |
| S9 Environment protection |  |  |  |
| S10 Action hardening |  |  |  |

### 11.3. Compliance verdict

| Поле | Значение |
|------|----------|
| Итоговый compliance level | C0 / C1 / C2 / C3 |
| Release decision | GO / GO-WAIVER / NO-GO |
| Основание |  |
| Открытые риски |  |
| Waiver expiry (если есть) |  |

### 11.4. Обязательные follow-up действия

| Action | Owner | Deadline | Status |
|--------|-------|----------|--------|
|  |  |  | open |

### 11.5. Audit trail

1. Ссылка на CI run:
2. Ссылка на scan reports:
3. Ссылка на SBOM artifacts:
4. Ссылка на sign/verify logs:
5. Ссылка на provenance:
6. Ссылка на deploy logs (staging/prod):
7. Ссылка на approval record:
