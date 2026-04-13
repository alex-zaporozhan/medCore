# Agent / automation notes (repository facts)

## CI/CD

- **VPS / demo (default for single-server deploy):** build images locally, then push to **Docker Hub** with interactive `docker login` — **`scripts/docker_hub_release.ps1`** or **`scripts/docker_hub_release.sh`**. See **`CI_CD.md`** and **`documentation/VPS_IMAGE_AND_DATA.md`**.
- **Optional GitHub Actions push to Hub:** **`.github/workflows/docker-hub-publish.yml`** — requires **`DOCKERHUB_USERNAME`** / **`DOCKERHUB_TOKEN`** secrets; **`workflow_dispatch`** or push tag **`v*`**; builds both images **before** login/push.
- **Docker smoke build (no push, no secrets):** **`.github/workflows/docker-images-build-verify.yml`**.
- **Team pipeline (when Jenkins is used):** **Jenkins** (`Jenkinsfile`) — build, push to **GHCR** (`ghcr.io`), deploy. No paid Docker Hub subscription required for that path.
- **GitHub Actions** under **`.github/workflows/`**: supplementary PR checks; they do **not** replace a configured Jenkins release unless your team uses only Hub + compose.

When suggesting CI changes, update **`Jenkinsfile`** (GHCR path), **`CI_CD.md`**, **`README.md`**, and the **`scripts/docker_hub_release.*`** helpers as appropriate.
