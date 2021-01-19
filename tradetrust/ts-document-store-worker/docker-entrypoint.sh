#!/usr/bin/env bash

set -euo pipefail

cd /document-store-worker

case "${CONTAINER_MODE,,}" in
  worker)
    npm run start
    ;;
  container)
    echo "Container started"
    tail -f /dev/null
    ;;
  *)
    echo "No mode specified" && exit 1
esac
