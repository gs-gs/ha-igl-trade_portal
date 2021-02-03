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

class ComposeBatch implements Task<void>{

  private startTimeMs!: number;
  private batchTimeMs: number;
  private batchSizeBytes: number;
  private unprocessedDocuments: UnprocessedDocuments;
  private batchDocuments: BatchDocuments;
  private unprocessedDocumentsQueue: UnprocessedDocumentsQueue;
  private messageWaitTime: number;
  private messageVisibilityTimeout: number;
  private documentStoreAddress: string;
  private batch: Batch;


  constructor({
    unprocessedDocuments,
    batchDocuments,
    unprocessedDocumentsQueue,
    batchTimeSeconds,
    batchSizeBytes,
    messageWaitTime,
    messageVisibilityTimeout,
    documentStoreAddress,
    batch
  }:{
    unprocessedDocuments: UnprocessedDocuments,
    batchDocuments: BatchDocuments,
    unprocessedDocumentsQueue: UnprocessedDocumentsQueue,
    batchTimeSeconds: number,
    batchSizeBytes: number,
    messageWaitTime: number,
    messageVisibilityTimeout: number,
    documentStoreAddress: string,
    batch: Batch
  }){
    this.unprocessedDocuments = unprocessedDocuments;
    this.batchDocuments = batchDocuments;
    this.unprocessedDocumentsQueue = unprocessedDocumentsQueue;
    this.batchTimeMs = batchTimeSeconds * 1000;
    this.batchSizeBytes = batchSizeBytes;
    this.messageWaitTime = messageWaitTime;
    this.messageVisibilityTimeout = messageVisibilityTimeout;
    this.documentStoreAddress = documentStoreAddress;
    this.batch = batch;
    if(1 > messageWaitTime || messageWaitTime > 20){
      throw Error('messageWaitTime must be >= 1 <=20');
    }
  }

  tryToCompleteBatch(batch: Batch){
    logger.debug('tryToCompleteBatch');
    const timeComplete = (Date.now() - this.startTimeMs) >= this.batchTimeMs;
    const sizeComplete = batch.size() >= this.batchSizeBytes;
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
    /* istanbul ignore next */
    if(!version){
      logger.warn('Unknown document version');
    }
    /* istanbul ignore next */
    if(!documentStoreAddress){
      logger.warn('Document store address not found');
    }
    /* istanbul ignore next */
    if(documentStoreAddress!==this.documentStoreAddress){
      logger.warn(
          'Unexpected document store address, got: "%s" expected: %s',
          documentStoreAddress, this.documentStoreAddress
      );
    }
    return version!==null && documentStoreAddress === this.documentStoreAddress
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

  async addDocumentToBatch(document: any){
    logger.debug('addDocumentToBatch')
    await this.batchDocuments.put({Key: document.key, Body: document.body.string});
    await this.unprocessedDocuments.delete({Key: document.key});
    this.batch.unwrappedDocuments.set(document.key, {
      size: document.size,
      body: document.body.json
    });
  }

  async processDocumentPutEvent(event: any){
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


  async tryToRestoreUnfinishedBatch(){
    logger.debug('tryToRestoreUnfinishedBatch');
    logger.info('Checking a batch backup bucket...');
    if(!await this.batchDocuments.isEmpty()){
      logger.info('The batch backup bucket is not empty, restoring previous batch');
      this.restoreUnfinishedBatch(this.batch);
    }else{
      logger.info('The batch backup bucket is empty, continuing normally');
    }
  }

  async tryToPrepareBatchForComposition(){
    logger.debug('tryToPrepareBatchForComposition');
    if(!this.batch.isEmpty()){
      throw new Error('Can not use non empty batches in compose task!');
    }
    logger.info(
      'Starting composing a new batch. Constraints SIZE: %s bytes, TIME: %s ms',
      this.batchSizeBytes, this.batchTimeMs
    );
    this.startTimeMs = Date.now();
    this.batch.composed = false;
    this.batch.wrapped = false;
    this.batch.issued = false;
    this.batch.saved = false;
    logger.info('Start time %s', new Date(this.startTimeMs));
  }

  async next(){
    logger.debug('next');
    // get the ObjectCreated:Put event from the unprocessed bucket
    let event: any| undefined;
    try{
      event = await this.getNextDocumentPutEvent();
    }catch(e){
      logger.error('An unexpected error happened during an attemp to get and parse Document PUT event');
      logger.error(e);
      return;
    }
    if(!event){
      return;
    }
    logger.info('Document PUT event found, trying to add the document to batch...');
    // if any unexpected error will happen during this stage, the event will no be deleted
    // and another attempt to add a document to the batch will be made until the document is not in a batch
    // or until the event is not put into a dead letters queue
    try{
      await this.processDocumentPutEvent(event);
    }catch(e){
      logger.error('An unexpected error happened during Document PUT event processing, event will not be deleted');
      logger.error(e);
      return;
    }
    // if everything is processed correctly, the event will point to a non-existent document, which will cause a KeyError
    // that will be handled gracefully
    try{
      await this.unprocessedDocumentsQueue.delete({ReceiptHandle: event.ReceiptHandle});
      logger.info('The document event processed succesfully, deleting it');
    }catch(e){
      logger.error('An unexpected error happend during an attempt to delete processed event');
      logger.error(e);
    }
  }

  async start(){
    logger.debug('start');

    await this.tryToPrepareBatchForComposition();

    try{
      await this.tryToRestoreUnfinishedBatch();
    }catch(e){
      logger.error('An unexpected error happened during batch restoration,  administrative actions required');
      logger.error(e);
      return;
    }

    while(!this.tryToCompleteBatch(this.batch)){
      await this.next();
    }

    logger.info('The batch is composed');
    this.batch.composed = true;
    return;
  }
}


export default ComposeBatch;
