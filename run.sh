#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-localhost/linux-update-checker-test}"
ENV_FILE="${ENV_FILE:-.env.development}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing env file: ${ENV_FILE}" >&2
  exit 1
fi

podman run --rm -it \
  --env-file "${ENV_FILE}" \
  "${IMAGE_NAME}" \
  "$@"
