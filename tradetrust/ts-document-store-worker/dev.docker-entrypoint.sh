#!/usr/bin/env bash

set -euo pipefail

cd /document-store-worker

case "${CONTAINER_MODE,,}" in
  batched-issue-worker)
    npm run start-batched-issue-worker
    ;;
  batched-revoke-worker)
    npm run start-batched-revoke-worker
    ;;
  container)
    echo "Container started"
    tail -f /dev/null
    ;;
  *)
    echo "No mode specified" && exit 1
esac
