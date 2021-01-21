import {
  SchemaId,
  wrapDocument
} from '@govtechsg/open-attestation';
import {
  UnprocessedDocuments,
  BatchDocuments,
  UnprocessedDocumentsQueue
} from '../repos';
import {
  OPEN_ATTESTATION_VERSION_ID_V2_SHORT,
  OPEN_ATTESTATION_VERSION_ID_V3_SHORT,
  DOCUMENT_STORE_PROOF_TYPE
} from '../constants';
import { logger } from '../logger';
import { Batch } from './data';
import { Task } from './interfaces';

class ComposeBatch implements Task<Promise<Batch>>{

  private maxBatchTimeMs: number;
  private batch!: Batch;

  constructor(
    private unprocessedDocuments: UnprocessedDocuments,
    private batchDocuments: BatchDocuments,
    private unprocessedDocumentsQueue: UnprocessedDocumentsQueue,
    maxBatchTimeSeconds: number,
    private maxBatchSizeBytes: number,
    private messageWaitTime: number,
    private documentStoreAddress: string,
  ){
    this.maxBatchTimeMs = maxBatchTimeSeconds * 1000;
    if(1 > messageWaitTime || messageWaitTime > 20){
      throw Error('messageWaitTime must be >= 1 <=20');
    }
  }

  tryToCompleteBatch(batch: Batch){
    logger.debug('tryToCompleteBatch');
    const timeComplete = (Date.now() - batch.creationTimestampMs) >= this.maxBatchTimeMs;
    const sizeComplete = batch.size() >= this.maxBatchSizeBytes;
    return timeComplete || sizeComplete;
  }

  async getNextDocumentPutEvent(){
    logger.debug('getNextDocumentPutEvent');
    const event = await this.unprocessedDocumentsQueue.get({
     VisibilityTimeout: 60,
     WaitTimeSeconds: this.messageWaitTime
    });
    if(event === null){return null;}
    event.Body = JSON.parse(event.Body);
    if(event.Body.Records.length == 0 || event.Body.Records.length > 1){return null};
    if(event.Body.Records[0].eventName !== 'ObjectCreated:Put'){return null};
    return event;
  }

  getDocumentStoreAddress(document: any, version: SchemaId.v2|SchemaId.v3|undefined): string|undefined{
    logger.debug('getDocumentStoreAddress');
    if(version === SchemaId.v2){
      return document?.issuers?.[0]?.documentStore;
    }else if(version === SchemaId.v3){
      return document?.proof?.method===DOCUMENT_STORE_PROOF_TYPE?document.proof.value: undefined;
    }
  }

  getDocumentVersion(document: any): SchemaId.v2|SchemaId.v3|undefined{
    logger.debug('getDocumentVersion');
    switch(document.version){
      case SchemaId.v2:
      case OPEN_ATTESTATION_VERSION_ID_V2_SHORT:
        return SchemaId.v2;
      case SchemaId.v3:
      case OPEN_ATTESTATION_VERSION_ID_V3_SHORT:
        return SchemaId.v3;
    }
  }

  verifyDocumentData(document: any): boolean{
    logger.debug('verifyDocumentData');
    try{
      wrapDocument(document);
    }catch(e){
      if(!!e.validationErrors){
        logger.debug(e.validationErrors);
        logger.debug('unknown document schema');
        return false;
      }
      throw e;
    }
    const version = this.getDocumentVersion(document);
    const documentStoreAddress = this.getDocumentStoreAddress(document, version);
    if(!version){
      logger.debug('unknown document version');
    }
    if(!documentStoreAddress){
      logger.debug('document store address not found');
    }
    if(documentStoreAddress!==this.documentStoreAddress){
      logger.debug(
          'unexpected document store address, got: "%s" expected: %s',
          documentStoreAddress, this.documentStoreAddress
      );
    }
    return version!==null && documentStoreAddress === this.documentStoreAddress
  }

  async getDocumentDataFromEvent(event: any){
    logger.debug('getDocumentDataFromEvent');
    const s3Object = event.Body.Records[0].s3.object;
    const documentObject = await this.unprocessedDocuments.get({Key: s3Object.key});
    const documentStringBody = documentObject.Body!.toString();
    const documentJSONBody = JSON.parse(documentStringBody);
    return {
      key: s3Object.key,
      size: s3Object.size,
      body: {
        string: documentStringBody,
        json: documentJSONBody
      }
    };
  }

  async addDocumentToBatch(document: any){
    logger.debug('addDocumentToBatch');
    // backing up batch files
    await this.batchDocuments.put({Key: document.key, Body: document.body.string});
    await this.unprocessedDocuments.delete({Key: document.key});
    this.batch.unwrappedDocuments.set(document.key, {
      size: document.size,
      body: document.body.json
    });
  }

  async next(){
    logger.debug('next')
    // get the ObjectCreated:Put event from the unprocessed bucket
    const event = await this.getNextDocumentPutEvent();
    if(!event){
      logger.debug('no event found')
      return;
    }
    logger.debug('event found')
    const document = await this.getDocumentDataFromEvent(event);

    if(this.verifyDocumentData(document.body.json)){
      await this.addDocumentToBatch(document);
    }
    // deleting the event after it processed
    await this.unprocessedDocumentsQueue.delete({ReceiptHandle: event.ReceiptHandle});
    logger.debug('event deleted')
  }

  async start(): Promise<Batch>{
    logger.debug('start');
    // create new batch object
    this.batch = new Batch();
    // check should this batch be sent for wrapping or not
    while(!this.tryToCompleteBatch(this.batch)){
      await this.next();
    }
    return this.batch;
  }
}


export default ComposeBatch;
