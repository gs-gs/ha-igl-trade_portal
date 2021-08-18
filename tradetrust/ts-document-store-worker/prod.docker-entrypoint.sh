#!/usr/bin/env sh

set -euo pipefail

cd /document-store-worker

# TODO: implement startup switch once cmdb changes in place to pass in mode
npm run start-batched-issue-worker
