#!/usr/bin/env bash
# Build backend + frontend locally, then push to Docker Hub (password at prompt).
# Usage: ./scripts/docker_hub_release.sh [tag]
#   DOCKERHUB_USERNAME=myuser ./scripts/docker_hub_release.sh v1.0.0
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TAG="${1:-latest}"
USER_NAME="${DOCKERHUB_USERNAME:-}"
if [[ -z "${USER_NAME}" ]]; then
  read -r -p "Docker Hub username (namespace): " USER_NAME
fi
USER_NAME="$(echo -n "$USER_NAME" | tr -d '[:space:]')"
if [[ -z "${USER_NAME}" ]]; then
  echo "Docker Hub username is required." >&2
  exit 1
fi

BACKEND="${USER_NAME}/dental-booking-backend:${TAG}"
FRONTEND="${USER_NAME}/dental-booking-frontend:${TAG}"

echo "Building backend -> ${BACKEND}"
docker build -t "${BACKEND}" -f Dockerfile .

echo "Building frontend -> ${FRONTEND}"
docker build -t "${FRONTEND}" -f Dockerfile ./frontend

echo "Build OK. Docker Hub login (password at prompt)..."
docker login docker.io -u "${USER_NAME}"

echo "Pushing ${BACKEND}"
docker push "${BACKEND}"

echo "Pushing ${FRONTEND}"
docker push "${FRONTEND}"

echo "Done. On the VPS set in .env, for example:"
echo "  BACKEND_IMAGE=docker.io/${BACKEND}"
echo "  FRONTEND_IMAGE=docker.io/${FRONTEND}"
