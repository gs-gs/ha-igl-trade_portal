#!/usr/bin/env bash


if [[ -z "$OA_API_LAMBDA_ZIP_FILENAME" ]]; then
  echo "OA API LAMBDA DEPLOYMENT SKIPPED"
else
  deploy_apigateway_lambda \
    $OA_API_LAMBDA_ZIP_FILENAME\
    $OA_API_LAMBDA_NAME\
    $OA_API_NAME\
    $OA_API_ENDPOINT_FILENAME
fi
