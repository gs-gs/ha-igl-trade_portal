import _ from 'lodash';
import config from '../src/config';
import {SQS, S3} from '../src/aws';
import DOCUMENT_V2_JSON from './data/document.v2.json';


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


function documentV2(overrides: object): any{
  const document = Object.assign(_.cloneDeep(DOCUMENT_V2_JSON), overrides);
  document.issuers[0].documentStore = config.DOCUMENT_STORE_ADDRESS;
  return document;
}


export {
  documentV2,
  clearQueue,
  clearBucket
}
