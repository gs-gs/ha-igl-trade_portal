import AWS, {S3, SQS, KMS} from './aws';
import {
  IBatchedIssueConfig,
  IBatchedDocumentStoreTaskConfig,
  IBatchedRevokeConfig,
} from './config';

const S3Service = S3({});
const SQSService = SQS({});
const KMSService = KMS({});

interface BucketPutRequest{
  Key: string,
  Body: string
}

interface BucketGetRequest{
  Key: string,
  IfMatch?: string
}

interface BucketDeleteRequest{
  Key: string
}

interface BatchListRequest{
  Prefix?: string,
  ContinuationToken?: string
  MaxKeys?: number
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
  async list(params?: BatchListRequest){
    return S3Service.listObjectsV2({Bucket: this.bucket, ...params??{}}).promise();
  }
  async isEmpty(){
    return !!((await this.list({MaxKeys: 1})).Contents?.length == 0)
  }
}

class Keys{

  private static BASE64_PREFIX_2: string = 'kms+base64:';
  private static BASE64_PREFIX_1: string = 'base64:';

  static async decrypt(data: string){
    const decrypted = await KMSService.decrypt({CiphertextBlob: data}).promise();
    return decrypted.Plaintext?.toString('utf-8')??'';
  }

  static async getStringOrB64KMS(data: string): Promise<string>{
    if(data.startsWith(this.BASE64_PREFIX_1)){
      data = data.slice(this.BASE64_PREFIX_1.length);
      data = Buffer.from(data, 'base64').toString('utf-8');
      return await this.decrypt(data);
    }else if(data.startsWith(this.BASE64_PREFIX_2)){
      data = data.slice(this.BASE64_PREFIX_2.length);
      data = Buffer.from(data, 'base64').toString('utf-8');
      return await this.decrypt(data);
    }
    return data;
  }
}

interface QueueGetRequest{
  VisibilityTimeout?: number,
  WaitTimeSeconds?: number
}

interface QueueDeleteRequest{
  ReceiptHandle: string
}

interface QueuePostRequest{
  MessageBody: string,
  DelaySeconds?: number
}

class Queue{
  queue_url: string;
  constructor(queue_url: string = ''){
    this.queue_url = queue_url;
  }

  async post(params: QueuePostRequest): Promise<any>{
    return await SQSService.sendMessage({QueueUrl: this.queue_url, ...params}).promise();
  }
  async get(params?: QueueGetRequest): Promise<AWS.SQS.Message|null>{
    const r = await SQSService.receiveMessage({QueueUrl: this.queue_url, MaxNumberOfMessages: 1, ...params}).promise();
    return r.Messages?r.Messages[0]:null;
  }
  async delete(params: QueueDeleteRequest){
    return SQSService.deleteMessage({QueueUrl: this.queue_url, ...params}).promise();
  }
}

class InvalidDocuments extends Bucket{
  constructor(config: IBatchedDocumentStoreTaskConfig){
    super(config.INVALID_BUCKET_NAME);
  }
}

class UnprocessedDocuments extends Bucket{
  constructor(config: IBatchedDocumentStoreTaskConfig){
    super(config.UNPROCESSED_BUCKET_NAME);
  }
}

class BatchDocuments extends Bucket{
  constructor(config: IBatchedDocumentStoreTaskConfig){
    super(config.BATCH_BUCKET_NAME);
  }
}

class IssuedDocuments extends Bucket{
  constructor(config: IBatchedIssueConfig){
    super(config.ISSUED_BUCKET_NAME);
  }
}

class RevokedDocuments extends Bucket{
  constructor(config: IBatchedRevokeConfig){
    super(config.REVOKED_BUCKET_NAME);
  }
}

class UnprocessedDocumentsQueue extends Queue{
  constructor(config: IBatchedDocumentStoreTaskConfig){
    super(config.UNPROCESSED_QUEUE_URL);
  }
}


export {
  Keys,
  Bucket,
  Queue,
  InvalidDocuments,
  UnprocessedDocuments,
  BatchDocuments,
  IssuedDocuments,
  RevokedDocuments,
  UnprocessedDocumentsQueue
}
