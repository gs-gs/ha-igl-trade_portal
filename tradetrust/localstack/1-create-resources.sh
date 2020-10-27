#!/usr/bin/env bash

set -eo pipefail
echo "Creating resources..."
echo "Creating queues..."
awslocal sqs create-queue --queue-name "unprocessed" --output text > /dev/null
echo "Done"
echo "Creating buckets..."
awslocal s3api create-bucket --bucket "unprocessed"
awslocal s3api create-bucket --bucket "issued"
echo "Done"
echo "Creating notifications..."
awslocal s3api put-bucket-notification --bucket unprocessed --notification-configuration file:///docker-entrypoint-initaws.d/notification.json
echo "Done"
awslocal sqs list-queues --output table
awslocal s3api list-buckets --output table
