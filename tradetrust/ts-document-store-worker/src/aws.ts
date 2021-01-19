import AWS from 'aws-sdk';
import config from './config';


function S3(conf?: AWS.S3.ClientConfiguration): AWS.S3{
  conf = conf || {};
  const defaultConfig = {
    endpoint: config.AWS_ENDPOINT_URL,
    s3ForcePathStyle: config.AWS_ENDPOINT_URL!==undefined
  }
  return new AWS.S3({...defaultConfig, ...conf});
}

function SQS(conf?: AWS.SQS.ClientConfiguration): AWS.SQS{
  conf = conf || {};
  const defaultConfig = {
    endpoint: config.AWS_ENDPOINT_URL
  }
  return new AWS.SQS({...defaultConfig, ...conf});
}

export {SQS, S3};

export default AWS;
