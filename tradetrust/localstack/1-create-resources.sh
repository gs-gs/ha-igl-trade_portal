#!/usr/bin/env bash

set -eo pipefail
echo "Creating resources..."

echo "Creating queues..."
awslocal sqs create-queue --queue-name "unprocessed" --output text > /dev/null
echo "Done"

# V2 notification queues
echo "Creating 2.0 queues..."
awslocal sqs create-queue --queue-name "revoke-unprocessed-2.0" --output text > /dev/null
awslocal sqs create-queue --queue-name "issue-unprocessed-2.0" --output text > /dev/null
echo "Done"

# V3 notification queues
echo "Creating 3.0 queues..."
awslocal sqs create-queue --queue-name "revoke-unprocessed-3.0" --output text > /dev/null
awslocal sqs create-queue --queue-name "issue-unprocessed-3.0" --output text > /dev/null
echo "Done"
echo "Queues created"

echo "Creating buckets..."
awslocal s3api create-bucket --bucket "unprocessed" > /dev/null
awslocal s3api create-bucket --bucket "batch" > /dev/null
awslocal s3api create-bucket --bucket "revoke-batch" > /dev/null
awslocal s3api create-bucket --bucket "issue-batch" > /dev/null
awslocal s3api create-bucket --bucket "issued" > /dev/null
awslocal s3api create-bucket --bucket "revoked" > /dev/null
awslocal s3api create-bucket --bucket "invalid" > /dev/null
awslocal s3api create-bucket --bucket "revoke-invalid" > /dev/null
awslocal s3api create-bucket --bucket "issue-invalid" > /dev/null
echo "Done"

# V2 buckets
echo "Creating 2.0 buckets..."
awslocal s3api create-bucket --bucket "revoke-unprocessed-2.0" > /dev/null
awslocal s3api create-bucket --bucket "issue-unprocessed-2.0" > /dev/null
awslocal s3api create-bucket --bucket "batch-2.0" > /dev/null
awslocal s3api create-bucket --bucket "revoke-batch-2.0" > /dev/null
awslocal s3api create-bucket --bucket "issue-batch-2.0" > /dev/null
awslocal s3api create-bucket --bucket "issued-2.0" > /dev/null
awslocal s3api create-bucket --bucket "revoked-2.0" > /dev/null
awslocal s3api create-bucket --bucket "invalid-2.0" > /dev/null
awslocal s3api create-bucket --bucket "revoke-invalid-2.0" > /dev/null
awslocal s3api create-bucket --bucket "issue-invalid-2.0" > /dev/null
echo "Done"

# V3 buckets
echo "Creating 3.0 buckets"
awslocal s3api create-bucket --bucket "revoke-unprocessed-3.0" > /dev/null
awslocal s3api create-bucket --bucket "issue-unprocessed-3.0" > /dev/null
awslocal s3api create-bucket --bucket "batch-3.0" > /dev/null
awslocal s3api create-bucket --bucket "revoke-batch-3.0" > /dev/null
awslocal s3api create-bucket --bucket "issue-batch-3.0" > /dev/null
awslocal s3api create-bucket --bucket "issued-3.0" > /dev/null
awslocal s3api create-bucket --bucket "revoked-3.0" > /dev/null
awslocal s3api create-bucket --bucket "invalid-3.0" > /dev/null
awslocal s3api create-bucket --bucket "revoke-invalid-3.0" > /dev/null
awslocal s3api create-bucket --bucket "issue-invalid-3.0" > /dev/null
echo "Done"
echo "Buckets created"

echo "Creating notifications..."
awslocal s3api put-bucket-notification --bucket unprocessed --notification-configuration file:///docker-entrypoint-initaws.d/notification.json
echo "Done"

# V2 notifications
echo "Creating 2.0 notifications"
awslocal s3api put-bucket-notification --bucket issue-unprocessed-2.0 --notification-configuration file:///docker-entrypoint-initaws.d/issue-notification-2.0.json
awslocal s3api put-bucket-notification --bucket revoke-unprocessed-2.0 --notification-configuration file:///docker-entrypoint-initaws.d/revoke-notification-2.0.json
echo "Done"

# V3 notifications
echo "Creating 3.0 notifications"
awslocal s3api put-bucket-notification --bucket issue-unprocessed-3.0 --notification-configuration file:///docker-entrypoint-initaws.d/issue-notification-3.0.json
awslocal s3api put-bucket-notification --bucket revoke-unprocessed-3.0 --notification-configuration file:///docker-entrypoint-initaws.d/revoke-notification-3.0.json
echo "Done"
echo "Notifications created"
echo "Resources created"
awslocal sqs list-queues --output table
awslocal s3api list-buckets --output table
