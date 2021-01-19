import AWS, {S3, SQS} from './aws';
import config from './config';


const S3Service = S3({});
const SQSService = SQS({});


interface BucketPutRequest{
  Key: string,
  Body: string
}

interface BucketGetRequest{
  Key: string
}

interface BucketDeleteRequest{
  Key: string
}

class Bucket{
  bucket: string;
  constructor(bucket: string = ''){
    this.bucket = bucket;
  }
  async put(params: BucketPutRequest){
    return S3Service.putObject({Bucket: this.bucket, ...params}).promise();
  }
  async get(params: BucketGetRequest){
    return S3Service.getObject({Bucket: this.bucket, ...params}).promise();
  }
  async delete(params: BucketDeleteRequest){
    return S3Service.deleteObject({Bucket: this.bucket, ...params}).promise();
  }
}

interface QueueGetRequest{
  VisibilityTimeout?: number,
  WaitTimeSeconds?: number
}

interface QueueDeleteRequest{
  ReceiptHandle: string
}

class Queue{
  queue_url: string;
  constructor(queue_url: string = ''){
    this.queue_url = queue_url;
  }
  async get(params?: QueueGetRequest): Promise<any|null>{
    const r = await SQSService.receiveMessage({QueueUrl: this.queue_url, MaxNumberOfMessages: 1, ...params}).promise();
    return r.Messages?r.Messages[0]:null;
  }
  async delete(params: QueueDeleteRequest){
    return SQSService.deleteMessage({QueueUrl: this.queue_url, ...params}).promise();
  }
}


class UnprocessedDocuments extends Bucket{
  constructor(){
    super(config.UNPROCESSED_BUCKET_NAME);
  }
}

class BatchDocuments extends Bucket{
  constructor(){
    super(config.BATCH_BUCKET_NAME);
  }
}

class IssuedDocuments extends Bucket{
  constructor(){
    super(config.ISSUED_BUCKET_NAME);
  }
}

class UnprocessedDocumentsQueue extends Queue{
  constructor(){
    super(config.UNPROCESSED_QUEUE_URL);
  }
}


export {
  Bucket,
  Queue,
  UnprocessedDocuments,
  BatchDocuments,
  IssuedDocuments,
  UnprocessedDocumentsQueue
}
