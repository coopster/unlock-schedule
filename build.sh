#!/usr/bin/env bash
set -euo pipefail
APP_VERSION="${APP_VERSION:-$(git rev-parse --short HEAD 2>/dev/null || echo dev)}"
docker build --build-arg APP_VERSION="${APP_VERSION}" -t unlock-schedule:latest .
