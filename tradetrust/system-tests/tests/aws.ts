import {
  AWS_ENDPOINT_URL
} from 'tests/env';
import AWS from 'aws-sdk';

function S3(conf?: AWS.S3.ClientConfiguration): AWS.S3{
  conf = conf || {};
  const defaultConfig = {
    endpoint: AWS_ENDPOINT_URL,
    s3ForcePathStyle: true
  };
  return new AWS.S3({...defaultConfig, ...conf});
}

function SQS(conf?: AWS.SQS.ClientConfiguration): AWS.SQS{
  conf = conf || {};
  const defaultConfig = {
    endpoint: AWS_ENDPOINT_URL
  };
  return new AWS.SQS({...defaultConfig, ...conf});
}

export {SQS, S3, AWS};
