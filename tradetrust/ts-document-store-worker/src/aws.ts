import AWS from 'aws-sdk';
import { getAWSEnvConfig } from './config';


function S3(conf?: AWS.S3.ClientConfiguration): AWS.S3{
  conf = conf || {};
  const config = getAWSEnvConfig();
  const defaultConfig = {
    endpoint: config.AWS_ENDPOINT_URL,
    s3ForcePathStyle: config.AWS_ENDPOINT_URL!==undefined
  };
  return new AWS.S3({...defaultConfig, ...conf});
}

function SQS(conf?: AWS.SQS.ClientConfiguration): AWS.SQS{
  conf = conf || {};
  const config = getAWSEnvConfig();
  const defaultConfig = {
    endpoint: config.AWS_ENDPOINT_URL
  };
  return new AWS.SQS({...defaultConfig, ...conf});
}

function KMS(conf: AWS.KMS.ClientConfiguration): AWS.KMS{
  conf = conf || {};
  const config = getAWSEnvConfig();
  const defaultConfig = {
    endpoint: config.AWS_ENDPOINT_URL
  };
  return new AWS.KMS({...defaultConfig, ...conf});
}

export {SQS, S3, KMS};

export default AWS;
