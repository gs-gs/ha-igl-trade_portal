#!/usr/bin/env bash

SLEEP="${SLEEP:-1}"
for ((i = 0 ; i < "$SLEEP" ; i++)); do
  echo "sleep $i/$SLEEP seconds"
  sleep 1
done

case "${CONTAINER_MODE,,}" in
  production)
    make run
    ;;
  development)
    make test || exit 1
    make run-debug
    ;;
  test)
    make test
    ;;
  container)
    echo "Container started"
    tail -f /dev/null
    ;;
  *)
    echo "No mode specified" && exit 1
esac
