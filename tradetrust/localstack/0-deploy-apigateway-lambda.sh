function deploy_apigateway_lambda(){

  API_LAMBDA_ZIP_FILENAME="$1"; shift
  API_LAMBDA_NAME="$1"; shift
  API_NAME="$1"; shift
  API_ENDPOINT_FILENAME="$1"; shift

  set -euo pipefail

  echo "Starting lambda and api gateway creation..."

  echo "Checking $API_LAMBDA_ZIP_FILENAME..."
  while [[ ! -e "$API_LAMBDA_ZIP_FILENAME" ]]; do
    echo "File $API_LAMBDA_ZIP_FILENAME does not exist. Waiting 1 sec, then check again..."
    sleep 1
  done
  echo "Found $API_LAMBDA_ZIP_FILENAME"


  echo "Creating lambda... using fileb://${API_LAMBDA_ZIP_FILENAME}"
  awslocal lambda create-function \
    --function-name $API_LAMBDA_NAME \
    --zip-file "fileb://${API_LAMBDA_ZIP_FILENAME}" \
    --handler src/index.handler \
    --runtime nodejs12.x \
    --role arn:aws:iam::123456789012:role/lambda-dummy-role
  echo "Done"

  LAMBDA_ARN=$(awslocal lambda list-functions --query "Functions[?FunctionName=='$API_LAMBDA_NAME'].FunctionArn" --output text)
  echo "LAMBDA_ARN=$LAMBDA_ARN"


  echo "Creating rest api..."
  function get_api_id(){
    awslocal apigateway get-rest-apis --query "items[?name=='$API_NAME'].id" --output text
  }
  API_ID=$(get_api_id)
  if [[ -z "$API_ID" ]]; then
    awslocal apigateway create-rest-api --name $API_NAME
    API_ID=$(get_api_id)
  fi
  echo "Done"
  PARENT_RESOURCE_ID=$(awslocal apigateway get-resources --rest-api-id ${API_ID} --query 'items[?path==`/`].id' --output text)
  echo "API_ID=$API_ID"
  echo "PARENT_RESOURCE_ID=$PARENT_RESOURCE_ID"


  echo "Creating proxy path..."
  function get_path_resource_id(){
    awslocal apigateway get-resources --rest-api-id ${API_ID} --query "items[?path=='/{proxy+}'].id" --output text
  }
  RESOURCE_ID=$(get_path_resource_id)
  if [[ -z "$RESOURCE_ID" ]]; then
    awslocal apigateway create-resource --rest-api-id $API_ID --parent-id $PARENT_RESOURCE_ID --path-part "{proxy+}"
    RESOURCE_ID=$(get_path_resource_id)
  fi
  echo "Done"
  echo "RESOURCE_ID=$RESOURCE_ID"

  echo "Integrating lambda to api gateway..."
  awslocal apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method ANY \
    --authorization-type "NONE"

  awslocal apigateway put-integration \
    --rest-api-id ${API_ID} \
    --resource-id ${RESOURCE_ID} \
    --http-method ANY \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri arn:aws:apigateway:${AWS_DEFAULT_REGION}:lambda:path/2015-03-31/functions/${LAMBDA_ARN}/invocations \
    --passthrough-behavior WHEN_NO_MATCH
  echo "Done"
  echo "Deploying api gateway"
  awslocal apigateway create-deployment \
    --rest-api-id ${API_ID} \
    --stage-name "test"
  echo "Done"

  echo "Saving API endpoint..."

  ENDPOINT=http://${HOSTNAME_EXTERNAL}:4567/restapis/${API_ID}/test/_user_request_/

  echo "$ENDPOINT" > $API_ENDPOINT_FILENAME
  echo "ENDPOINT=$ENDPOINT saved to $API_ENDPOINT_FILENAME"
  echo "Done"

  echo "Deleting used lambda zip archive..."
  rm $API_LAMBDA_ZIP_FILENAME
  echo "Done"
}
