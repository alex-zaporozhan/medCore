# Agent / automation notes (repository facts)

## CI/CD

- **Primary pipeline:** **Jenkins** (`Jenkinsfile`) — build, push container images, deploy.
- **Container registry:** **GHCR** (`ghcr.io`), not Docker Hub. No paid Docker Hub subscription is required for this project’s flow.
- **GitHub Actions** (`.github/workflows/`): supplementary checks on PRs/pushes; they do **not** replace Jenkins for image publish and production deploy.

When suggesting CI changes, prefer updating **`Jenkinsfile`** and this repo’s docs (`CI_CD.md`, `README.md`) rather than assuming GHA-only workflows.
