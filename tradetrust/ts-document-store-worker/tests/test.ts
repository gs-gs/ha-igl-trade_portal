import _ from 'lodash';
import {SQS, S3} from '../src/aws';
import config from '../src/config';
import {
  BatchDocuments,
  UnprocessedDocuments,
  UnprocessedDocumentsQueue
} from '../src/repos';
import {ComposeBatch} from '../src/tasks';
import DOCUMENT_V2 from './data/document.v2.json';

const S3Service = S3();
const SQSService = SQS();

async function clearBucket(Bucket: string){
  let response: any = {};
  do{
    response = await S3Service.listObjectsV2({
      Bucket,
      ContinuationToken: response.NextContinuationToken
    }).promise();
    for(let object of response.Contents || []){
      if(object.Key){
        await S3Service.deleteObject({Key: object.Key, Bucket}).promise()
      }
    }
  }while(response.IsTruncated);
}

async function clearQueue(QueueUrl: string){
  await SQSService.purgeQueue({QueueUrl}).promise();
}

describe('ComposeBatch Task', ()=>{
  const unprocessedDocuments = new UnprocessedDocuments();
  const batchDocuments = new BatchDocuments();
  const unprocessedDocumentsQueue = new UnprocessedDocumentsQueue();
  beforeEach(async ()=>{
    await clearBucket(config.BATCH_BUCKET_NAME);
    await clearBucket(config.UNPROCESSED_BUCKET_NAME);
    await clearBucket(config.ISSUED_BUCKET_NAME);
    await clearQueue(config.UNPROCESSED_QUEUE_URL);
  });
  test('Picking unwrapped document v2', async ()=>{
    const composeBatchTask = new ComposeBatch(
      unprocessedDocuments,
      batchDocuments,
      unprocessedDocumentsQueue,
      1024,
      60,
      20,
      config.DOCUMENT_STORE_ADDRESS
    );
    const document = _.cloneDeep(DOCUMENT_V2);
    document.issuers[0].documentStore = config.DOCUMENT_STORE_ADDRESS;
    unprocessedDocuments.put({Key:'document-v2-unwrapped', Body: JSON.stringify(document)});
    await composeBatchTask.next();
  });
});
