#!/usr/bin/env bash

set -eo pipefail
echo "Creating resources..."
echo "Creating queues..."
awslocal sqs create-queue --queue-name "unprocessed" --output text > /dev/null
awslocal sqs create-queue --queue-name "revoke-unprocessed" --output text > /dev/null
awslocal sqs create-queue --queue-name "issue-unprocessed" --output text > /dev/null
echo "Done"
echo "Creating buckets..."
awslocal s3api create-bucket --bucket "unprocessed"
awslocal s3api create-bucket --bucket "revoke-unprocessed"
awslocal s3api create-bucket --bucket "issue-unprocessed"
awslocal s3api create-bucket --bucket "batch"
awslocal s3api create-bucket --bucket "revoke-batch"
awslocal s3api create-bucket --bucket "issue-batch"
awslocal s3api create-bucket --bucket "issued"
awslocal s3api create-bucket --bucket "revoked"
awslocal s3api create-bucket --bucket "invalid"
awslocal s3api create-bucket --bucket "revoke-invalid"
awslocal s3api create-bucket --bucket "issue-invalid"
echo "Done"
echo "Creating notifications..."
awslocal s3api put-bucket-notification --bucket unprocessed --notification-configuration file:///docker-entrypoint-initaws.d/notification.json
awslocal s3api put-bucket-notification --bucket issue-unprocessed --notification-configuration file:///docker-entrypoint-initaws.d/issue-notification.json
awslocal s3api put-bucket-notification --bucket revoke-unprocessed --notification-configuration file:///docker-entrypoint-initaws.d/revoke-notification.json
echo "Done"
awslocal sqs list-queues --output table
awslocal s3api list-buckets --output table
