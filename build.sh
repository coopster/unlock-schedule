#!/usr/bin/env bash
set -euo pipefail
APP_VERSION="${APP_VERSION:-$(git rev-parse --short HEAD 2>/dev/null || echo dev)}"
PLATFORM="${PLATFORM:-linux/amd64}"
OUTPUT="${OUTPUT:-load}" # "load" (local) or "tar" (transfer)
IMAGE_NAME="${IMAGE_NAME:-unlock-schedule}"
TAG="${TAG:-${APP_VERSION}}"

if ! docker buildx inspect unlock-schedule-builder >/dev/null 2>&1; then
  docker buildx create --name unlock-schedule-builder --use >/dev/null
else
  docker buildx use unlock-schedule-builder >/dev/null
fi

if [ "${OUTPUT}" = "tar" ]; then
  DEST="${DEST:-dist/${IMAGE_NAME}_${TAG}_${PLATFORM//\\//-}.tar}"
  mkdir -p "$(dirname "${DEST}")"
  docker buildx build \
    --platform "${PLATFORM}" \
    --build-arg APP_VERSION="${APP_VERSION}" \
    -t "${IMAGE_NAME}:${TAG}" \
    --output "type=tar,dest=${DEST}" \
    .
  echo "Wrote ${DEST}"
else
  docker buildx build \
    --platform "${PLATFORM}" \
    --build-arg APP_VERSION="${APP_VERSION}" \
    -t "${IMAGE_NAME}:${TAG}" \
    --load \
    .
fi
