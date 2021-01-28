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
  private startTimeMs!: number;


  constructor(
    private unprocessedDocuments: UnprocessedDocuments,
    private batchDocuments: BatchDocuments,
    private unprocessedDocumentsQueue: UnprocessedDocumentsQueue,
    maxBatchTimeSeconds: number,
    private maxBatchSizeBytes: number,
    private messageWaitTime: number,
    private messageVisibilityTimeout: number,
    private documentStoreAddress: string,
    private batch: Batch
  ){
    this.maxBatchTimeMs = maxBatchTimeSeconds * 1000;
    if(1 > messageWaitTime || messageWaitTime > 20){
      throw Error('messageWaitTime must be >= 1 <=20');
    }
  }

  tryToCompleteBatch(batch: Batch){
    logger.debug('tryToCompleteBatch');
    const timeComplete = (Date.now() - this.startTimeMs) >= this.maxBatchTimeMs;
    const sizeComplete = batch.size() >= this.maxBatchSizeBytes;
    return timeComplete || sizeComplete;
  }

  async getNextDocumentPutEvent(){
    logger.debug('getNextDocumentPutEvent');
    const event = await this.unprocessedDocumentsQueue.get({
      VisibilityTimeout: this.messageVisibilityTimeout,
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
        logger.warn('Unknown document schema', );
        logger.warn(e.validationErrors);
        return false;
      }
      throw e;
    }
    const version = this.getDocumentVersion(document);
    const documentStoreAddress = this.getDocumentStoreAddress(document, version);
    if(!version){
      logger.warn('Unknown document version');
    }
    if(!documentStoreAddress){
      logger.warn('Document store address not found');
    }
    if(documentStoreAddress!==this.documentStoreAddress){
      logger.warn(
          'Unexpected document store address, got: "%s" expected: %s',
          documentStoreAddress, this.documentStoreAddress
      );
    }
    return version!==null && documentStoreAddress === this.documentStoreAddress
  }


  async getDocumentDataFromEvent(event: any){
    logger.debug('getDocumentDataFromEvent');
    const s3Object = event.Body.Records[0].s3.object;
    let documentObject;
    try{
      logger.info('Trying do download the document. Key "%s"', s3Object.key);
      documentObject = await this.unprocessedDocuments.get({Key: s3Object.key});
    }catch(e){
      if(e.code === 'NoSuchKey'){
        return undefined;
      }
      throw e;
    }
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
    logger.debug('addDocumentToBatch')
    await this.batchDocuments.put({Key: document.key, Body: document.body.string});
    await this.unprocessedDocuments.delete({Key: document.key});
    this.batch.unwrappedDocuments.set(document.key, {
      size: document.size,
      body: document.body.json
    });
  }

  async next(){
    logger.debug('next');
    // get the ObjectCreated:Put event from the unprocessed bucket
    const event = await this.getNextDocumentPutEvent();
    if(!event){
      return;
    }
    logger.info('Document PUT event found, trying to add the document to batch...');
    const document = await this.getDocumentDataFromEvent(event);
    if(document !== undefined){
      logger.info('The document data downloaded succesfully, document key: %s', document?.key)
      if(this.verifyDocumentData(document.body.json)){
        logger.info('The document verified succesfully, adding data to the batch');
        await this.addDocumentToBatch(document);
      }else{
        logger.info('The document schema is invalid, skipping further operations');
      }
    }else{
      logger.warn('Document not found by the provided key, skipping further operations');
    }
    // deleting the event after it processed
    await this.unprocessedDocumentsQueue.delete({ReceiptHandle: event.ReceiptHandle});
    logger.info('The document event processed succesfully, deleting it');
  }

  async restoreUnfinishedBatch(batch: Batch){
    logger.debug('restoreUnfinishedBatch');
    // using tryToCompleteBatch is required to prevent erros if batch parameters were changed
    // after the last batch failed
    let ContinuationToken: string|undefined;
    do{
      for(let s3Object of (await this.batchDocuments.list({ContinuationToken})).Contents??[]){
        const documentObject = await this.batchDocuments.get({Key: s3Object!.Key!})
        const documentJSONBody = JSON.parse(documentObject.Body!.toString());
        batch.unwrappedDocuments.set(s3Object.Key!, {body: documentJSONBody, size: s3Object.Size!});
      }
    }while(ContinuationToken && !this.tryToCompleteBatch(batch));
  }

  async start(): Promise<Batch>{
    logger.debug('start');
    if(!this.batch.isEmpty()){
      throw new Error('Can not use non empty batches in compose task!');
    }
    logger.info(
      'Starting composing a new batch. Constraints SIZE: %s bytes, TIME: %s ms',
      this.maxBatchSizeBytes, this.maxBatchTimeMs
    );
    this.startTimeMs = Date.now();
    logger.info('Start time %s', new Date(this.startTimeMs));
    logger.info('Checking a batch backup bucket...');
    if(!await this.batchDocuments.isEmpty()){
      logger.info('The batch backup bucket is not empty, restoring previous batch');
      this.restoreUnfinishedBatch(this.batch);
    }else{
      logger.info('The batch backup bucket is empty, continuing normally');
    }
    while(!this.tryToCompleteBatch(this.batch)){
      await this.next();
    }
    logger.info('The batch is complete');
    return this.batch;
  }
}


export default ComposeBatch;
