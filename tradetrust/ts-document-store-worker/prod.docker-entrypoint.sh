#!/usr/bin/env sh

set -euo pipefail

cd /document-store-worker

STARTUP_DELAY_SECONDS="${STARTUP_DELAY_SECONDS:-}"
if [[ -n "$STARTUP_DELAY_SECONDS" ]]; then
  echo "Sleeping $STARTUP_DELAY_SECONDS"
  sleep $STARTUP_DELAY_SECONDS
fi

node $@
