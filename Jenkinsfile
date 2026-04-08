// CI/CD canonical pipeline for this repo: Jenkins (not GitHub Actions for image publish/deploy).
// Container registry: ghcr.io (GHCR). Docker Hub is not required; no paid Docker Hub assumption.
pipeline {
  agent any

  options {
    disableConcurrentBuilds()
    timestamps()
  }

  parameters {
    booleanParam(name: 'RUN_TESTS', defaultValue: true, description: 'Run backend/frontend tests before building images')
    booleanParam(name: 'DEPLOY', defaultValue: true, description: 'Deploy to VM after pushing images (main only)')
    string(name: 'REMOTE_APP_DIR', defaultValue: '/opt/dental_booking', description: 'Remote directory containing docker-compose.yml and .env')
    string(name: 'SMOKE_URL', defaultValue: 'http://localhost:8010/health', description: 'URL to check from remote host (curl) after deploy')
  }

  environment {
    GHCR_REGISTRY = 'ghcr.io'
    // Set GHCR_OWNER in Jenkins job env (e.g. github org/user), not in git.
    // Images will be: ghcr.io/${GHCR_OWNER}/dental-booking-backend and -frontend
    BACKEND_IMAGE_REPO = "${GHCR_REGISTRY}/${GHCR_OWNER}/dental-booking-backend"
    FRONTEND_IMAGE_REPO = "${GHCR_REGISTRY}/${GHCR_OWNER}/dental-booking-frontend"
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        sh 'git rev-parse --short HEAD'
      }
    }

    stage('Detect changes') {
      steps {
        script {
          def baseRef = env.GIT_PREVIOUS_SUCCESSFUL_COMMIT ?: ''
          def headRef = env.GIT_COMMIT ?: 'HEAD'
          def diffCmd = baseRef?.trim()
            ? "git diff --name-only ${baseRef}..${headRef}"
            : "git diff --name-only HEAD~1..${headRef} || true"

          def changed = sh(script: diffCmd, returnStdout: true).trim().split('\n') as List
          if (changed.size() == 1 && changed[0].trim() == '') { changed = [] }

          env.BACKEND_CHANGED = changed.any { it == 'Dockerfile' || it == 'pyproject.toml' || it == 'poetry.lock' || it.startsWith('src/') || it.startsWith('scripts/') || it.startsWith('alembic/') } ? 'true' : 'false'
          env.FRONTEND_CHANGED = changed.any { it.startsWith('frontend/') } ? 'true' : 'false'

          if (env.BACKEND_CHANGED != 'true' && env.FRONTEND_CHANGED != 'true') {
            // If we cannot reliably detect diff (e.g. first build), build both to keep main "no surprises".
            env.BACKEND_CHANGED = 'true'
            env.FRONTEND_CHANGED = 'true'
          }
          echo "backend_changed=${env.BACKEND_CHANGED}, frontend_changed=${env.FRONTEND_CHANGED}"
        }
      }
    }

    stage('Backend tests') {
      when { expression { return params.RUN_TESTS && env.BACKEND_CHANGED == 'true' } }
      steps {
        sh '''
          set -euo pipefail
          python --version || true
          pip --version || true
          poetry --version || (pip install poetry && poetry --version)
          poetry config virtualenvs.create false
          poetry install --no-interaction --no-ansi --with dev --no-root
          poetry run ruff check src tests
          poetry run python scripts/audit_tenant_columns.py
          poetry run mypy src/core/security.py --ignore-missing-imports --follow-imports=skip
          poetry run pip install pip-audit
          poetry run pip-audit
          poetry run pytest -v tests/ --ignore=tests/e2e --maxfail=1
        '''
      }
    }

    stage('Frontend tests') {
      when { expression { return params.RUN_TESTS && env.FRONTEND_CHANGED == 'true' } }
      steps {
        sh '''
          set -euo pipefail
          node --version
          npm --version
          cd frontend
          npm ci
          npm run lint
          npm run test -- --run
          npm run build
        '''
      }
    }

    stage('Login to GHCR') {
      when { expression { return env.BACKEND_CHANGED == 'true' || env.FRONTEND_CHANGED == 'true' } }
      steps {
        withCredentials([
          string(credentialsId: 'ghcr-token', variable: 'GHCR_TOKEN'),
          string(credentialsId: 'ghcr-username', variable: 'GHCR_USERNAME')
        ]) {
          sh '''
            set -euo pipefail
            echo "$GHCR_TOKEN" | docker login "$GHCR_REGISTRY" -u "$GHCR_USERNAME" --password-stdin
          '''
        }
      }
    }

    stage('Build & push backend') {
      when { expression { return env.BACKEND_CHANGED == 'true' } }
      steps {
        sh '''
          set -euo pipefail
          SHA="$(git rev-parse HEAD)"
          docker buildx create --name dental_booking_builder --use >/dev/null 2>&1 || docker buildx use dental_booking_builder
          docker buildx inspect --bootstrap >/dev/null
          docker buildx build \
            --file Dockerfile \
            --tag "${BACKEND_IMAGE_REPO}:${SHA}" \
            --tag "${BACKEND_IMAGE_REPO}:main" \
            --push \
            --metadata-file backend-metadata.json \
            .
        '''
        sh '''
          set -euo pipefail
          python - <<'PY'
import json
with open('backend-metadata.json','r',encoding='utf-8') as f:
    meta=json.load(f)
digest=meta.get('containerimage.digest') or meta.get('containerimage.digest[0]')
if not digest:
    raise SystemExit('backend digest not found in backend-metadata.json')
print(digest)
PY
        '''
        script {
          env.BACKEND_DIGEST = sh(script: "python - <<'PY'\nimport json\nm=json.load(open('backend-metadata.json','r',encoding='utf-8'))\nd=m.get('containerimage.digest') or m.get('containerimage.digest[0]')\nprint(d)\nPY", returnStdout: true).trim()
          echo "backend_digest=${env.BACKEND_DIGEST}"
        }
      }
    }

    stage('Build & push frontend') {
      when { expression { return env.FRONTEND_CHANGED == 'true' } }
      steps {
        sh '''
          set -euo pipefail
          SHA="$(git rev-parse HEAD)"
          docker buildx create --name dental_booking_builder --use >/dev/null 2>&1 || docker buildx use dental_booking_builder
          docker buildx inspect --bootstrap >/dev/null
          docker buildx build \
            --file frontend/Dockerfile \
            --tag "${FRONTEND_IMAGE_REPO}:${SHA}" \
            --tag "${FRONTEND_IMAGE_REPO}:main" \
            --push \
            --metadata-file frontend-metadata.json \
            frontend
        '''
        script {
          env.FRONTEND_DIGEST = sh(script: "python - <<'PY'\nimport json\nm=json.load(open('frontend-metadata.json','r',encoding='utf-8'))\nd=m.get('containerimage.digest') or m.get('containerimage.digest[0]')\nprint(d)\nPY", returnStdout: true).trim()
          echo "frontend_digest=${env.FRONTEND_DIGEST}"
        }
      }
    }

    stage('Deploy to VM (compose)') {
      when {
        allOf {
          branch 'main'
          expression { return params.DEPLOY }
          expression { return env.DEPLOY_HOST?.trim() }
        }
      }
      steps {
        sshagent(credentials: ['deploy-ssh-key']) {
          sh '''
            set -euo pipefail
            if [ -n "${BACKEND_DIGEST:-}" ]; then
              BACKEND_REF="${BACKEND_IMAGE_REPO}@${BACKEND_DIGEST}"
            else
              BACKEND_REF=""
              echo "INFO: BACKEND_DIGEST is empty; will keep remote BACKEND_IMAGE as-is"
            fi

            if [ -n "${FRONTEND_DIGEST:-}" ]; then
              FRONTEND_REF="${FRONTEND_IMAGE_REPO}@${FRONTEND_DIGEST}"
            else
              FRONTEND_REF=""
              echo "INFO: FRONTEND_DIGEST is empty; will keep remote FRONTEND_IMAGE as-is"
            fi

            ssh -o StrictHostKeyChecking=accept-new "$DEPLOY_SSH_USER@$DEPLOY_HOST" "mkdir -p '${REMOTE_APP_DIR}'"

            ssh -o StrictHostKeyChecking=accept-new "$DEPLOY_SSH_USER@$DEPLOY_HOST" "set -euo pipefail; cd '${REMOTE_APP_DIR}'; \
              if [ -f ./jenkins-images.env ]; then . ./jenkins-images.env; fi; \
              if [ -n '${BACKEND_REF}' ]; then BACKEND_IMAGE='${BACKEND_REF}'; fi; \
              if [ -n '${FRONTEND_REF}' ]; then FRONTEND_IMAGE='${FRONTEND_REF}'; fi; \
              test -n \"\${BACKEND_IMAGE:-}\"; test -n \"\${FRONTEND_IMAGE:-}\"; \
              cat > ./jenkins-images.env <<EOF\nBACKEND_IMAGE=\${BACKEND_IMAGE}\nFRONTEND_IMAGE=\${FRONTEND_IMAGE}\nEOF"

            ssh -o StrictHostKeyChecking=accept-new "$DEPLOY_SSH_USER@$DEPLOY_HOST" "set -euo pipefail; cd '${REMOTE_APP_DIR}'; set -a; [ -f .env ] && . ./.env || true; . ./jenkins-images.env; set +a; docker compose pull; docker compose up -d"

            ssh -o StrictHostKeyChecking=accept-new "$DEPLOY_SSH_USER@$DEPLOY_HOST" "set -euo pipefail; curl -fsS '${SMOKE_URL}' >/dev/null"
          '''
        }
      }
    }
  }

  post {
    always {
      sh 'docker logout ghcr.io >/dev/null 2>&1 || true'
      archiveArtifacts artifacts: '*-metadata.json', allowEmptyArchive: true
    }
  }
}

