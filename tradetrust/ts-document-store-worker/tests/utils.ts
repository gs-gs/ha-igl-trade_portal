import _ from 'lodash';
import { InvalidDocuments } from 'src/repos';
import { Batch } from 'src/tasks/common/data';
import { logger } from 'src/logger';
import { getDocumentStoreTaskEnvConfig } from 'src/config';
import {SQS, S3} from 'src/aws';
import DOCUMENT_V2_JSON from './data/document.v2.json';
import DOCUMENT_V3_JSON from './data/document.v3.json';


const config = getDocumentStoreTaskEnvConfig();

const S3Service = S3();
const SQSService = SQS();


export async function clearBucket(Bucket: string){
  logger.debug('tests.utils.clearBucket "%s"', Bucket);
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

export async function clearQueue(QueueUrl: string){
  logger.debug('tests.utils.clearQueue "%s"', QueueUrl);
  await SQSService.purgeQueue({QueueUrl}).promise();
}


export function documentV2(overrides: object = {}): any{
  const document = _.cloneDeep(DOCUMENT_V2_JSON);
  document.issuers[0].documentStore = config.DOCUMENT_STORE_ADDRESS;
  return _.merge(document, overrides);
}


export function documentV3(overrides: object = {}): any{
  const document = _.cloneDeep(DOCUMENT_V3_JSON);
  document.openAttestationMetadata.proof.value = `did:ethr:${config.DOCUMENT_STORE_ADDRESS}`;
  document.openAttestationMetadata.identityProof.identifier = document.openAttestationMetadata.proof.value;
  return _.merge(document, overrides);
}


export function generateDocumentsMapV2(documentsCount: number): Map<string, any>{
  const documents = new Map<string, any>();
  for(let documentIndex = 0; documentIndex < documentsCount; documentIndex++){
    const key = `document-key-${documentIndex}`
    const body = `document-body-${documentIndex}`
    documents.set(key, documentV2({body}));
  }
  return documents;
}


export function generateDocumentsMapV3(documentsCount: number): Map<string, any>{
  const documents = new Map<string,any>();
  for(let documentIndex = 0; documentIndex < documentsCount; documentIndex++){
    const key = `document-key-${documentIndex}`
    const credentialSubject = {
      id: `did:example:value-${documentIndex}`
    };
    documents.set(key, documentV3({credentialSubject}));
  }
  return documents;
}

export const createInvalidDocumentReasonAssert = (
  batch: Batch,
  documents: Map<string, any>,
  invalidDocuments: InvalidDocuments
)=>{
  return async (key: string, reason: string)=>{
    expect(batch.wrappedDocuments.get(key)).toBeFalsy();
    const invalidDocumentReasonBody = JSON.parse((await invalidDocuments.get({Key: `${key}.reason.json`})).Body?.toString()??'{}');
    const expectedDocumentBody = documents.get(key);
    if(typeof expectedDocumentBody === 'string'){
      const invalidDocumentBody = (await invalidDocuments.get({Key: key})).Body?.toString();
      expect(invalidDocumentBody).toMatch(documents.get(key));
    }else{
      const invalidDocumentBody = JSON.parse((await invalidDocuments.get({Key: key})).Body?.toString()??'{}');
      expect(invalidDocumentBody).toEqual(documents.get(key));
    }
    expect(invalidDocumentReasonBody).toEqual({
      reason: reason
    });
  }
}
