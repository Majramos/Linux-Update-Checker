#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-linux-update-checker-test}"
PKG_URL="${PKG_URL:-linux-update-checker @ git+https://gitlab.com/majramos/linux-update-checker.git}"

podman build \
  --build-arg PKG_URL="${PKG_URL}" \
  -t "${IMAGE_NAME}" \
  -f Containerfile \
  .
