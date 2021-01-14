import AWS from 'aws-sdk';

function S3(config: AWS.S3.ClientConfiguration): AWS.S3{
    const defaultConfig = {
      endpoint: process.env.AWS_ENDPOINT_URL,
      s3ForcePathStyle: process.env.AWS_ENDPOINT_URL!==undefined
    }
    return new AWS.S3({...defaultConfig, ...config})
}

function SQS(config: AWS.SQS.ClientConfiguration): AWS.SQS{
    const defaultConfig = {
      endpoint: process.env.AWS_ENDPOINT_URL
    }
    return new AWS.SQS({...defaultConfig, ...config})
}

export {SQS, S3}

export default AWS;
