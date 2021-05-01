import { logger } from 'tests/logger';
import { S3 as S3Client, SQS as SQSClient, AWS} from 'tests/aws';

const S3 = S3Client();
const SQS = SQSClient();

interface IBucketProps{
  Bucket: string
}

interface IBucketGetProps{
  Key: string
}

interface IBucketPutProps{
  Key: string
  Body: string
}

interface IBucketDeleteProps{
  Key: string
}

interface IBucketListProps{
  Prefix: string
}

class Bucket{

  private props: IBucketProps;

  constructor(props: IBucketProps){
    this.props = props;
  }

  async get({Key}: IBucketGetProps){
    try{
      return await S3.getObject({
        Bucket: this.props.Bucket,
        Key
      }).promise()
    }catch(e){
      if(e.code == 'NoSuchKey'){
        return;
      }
      throw e;
    }

  }

  async put({Body, Key}: IBucketPutProps){
    return await S3.putObject({
      Bucket: this.props.Bucket,
      Key,
      Body
    }).promise()
  }

  async delete({Key}: IBucketDeleteProps){
    return await S3.deleteObject({
      Bucket: this.props.Bucket,
      Key
    }).promise()
  }

  async list({Prefix}: IBucketListProps){
    let ContinuationToken = undefined;
    const list: Array<AWS.S3.Object> = [];
    do{
      const result: AWS.S3.ListObjectsV2Output = await S3.listObjectsV2({
        ContinuationToken,
        Bucket: this.props.Bucket,
        Prefix
      }).promise();
      ContinuationToken = result.ContinuationToken;
      for(let object of result.Contents??[]){
        list.push(object);
      }
    }while(ContinuationToken)
    return list;
  }
}

interface IRetryableBucketGetProps extends IBucketGetProps{
  Attempts: number,
  AttemptsInterval: number
}

async function sleep(seconds: number){
  return new Promise(r=>setTimeout(r, seconds * 1000));
}

class RetryableBucket extends Bucket{
  async get({
    Attempts,
    AttemptsInterval,
    Key
  }:IRetryableBucketGetProps){
    logger.info('Trying to get object. Key: %s', Key);
    for(let attempt = 0; attempt < Attempts; attempt++){
      logger.info('Attempt: %s/%s', attempt + 1, Attempts);
      const object = await super.get({Key});
      if(object){
        logger.info('Object found');
        return object;
      }else{
        logger.warn('Object not found, retrying...');
        await sleep(AttemptsInterval);
      }
    }
    logger.error('Ran out of attempts');
  }
}

export { Bucket, RetryableBucket }
