#!/usr/bin/env bash

set -euo pipefail

cd /open-attestation-api

case "${CONTAINER_MODE,,}" in
  server)
    npm run start
    ;;
  server-development)
    npm run server-development
    ;;
  lambda)
    echo "Creating a lambda archive..."
    echo "Creating archive directory if not exists..."
    mkdir -p "$(dirname $LAMBDA_ZIP_FILENAME)"
    npx serverless package
    cp .serverless/openatt-api.zip ${LAMBDA_ZIP_FILENAME}
    echo "All done. The archive saved as $LAMBDA_ZIP_FILENAME"
    ;;
  container)
    echo "Container started"
    tail -f /dev/null
    ;;
  *)
    echo "No mode specified" && exit 1
esac
