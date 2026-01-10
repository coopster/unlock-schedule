#!/usr/bin/env bash
set -euo pipefail
APP_VERSION="${APP_VERSION:-$(git rev-parse --short HEAD 2>/dev/null || echo dev)}"
PLATFORM="${PLATFORM:-linux/amd64}"
IMAGE_NAME="${IMAGE_NAME:-unlock-schedule}"
TAG="${TAG:-${APP_VERSION}}"
DEST="${DEST:-dist/${IMAGE_NAME}_${TAG}_${PLATFORM//\\//-}.tar}"

docker buildx build \
  --platform "${PLATFORM}" \
  --build-arg APP_VERSION="${APP_VERSION}" \
  -t "${IMAGE_NAME}:${TAG}" \
  --output "type=docker,dest=${DEST}" \
  .


