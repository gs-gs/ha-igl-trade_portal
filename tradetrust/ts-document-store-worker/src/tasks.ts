import pino from 'pino';
import {validateSchema, verifySignature, wrapDocuments, wrapDocument, SchemaId} from '@govtechsg/open-attestation';
import {
  connectDocumentStore
} from './document-store';
import {
  UnprocessedDocuments,
  BatchDocuments,
  UnprocessedDocumentsQueue
} from './repos';
import constants from './constants';



const logger = pino({level: 'debug'});


interface Task<T>{
  start(): T;
  next(): void
}

interface UnwrappedDocument{
  size: number,
  body: any
}

class Batch{
  creationTimestampMs: number = 0;
  unwrappedDocuments: Map<string, UnwrappedDocument>;
  wrappedDocuments: Array<any>;
  merkleRoot: string = '';

  constructor(){
    this.creationTimestampMs = Date.now();
    this.unwrappedDocuments = new Map<string, UnwrappedDocument>();
    this.wrappedDocuments = [];
  }

  size(){
    let size = 0;
    for(let [, document] of this.unwrappedDocuments){size += document.size}
    return size;
  }

}

class ComposeBatch implements Task<Promise<Batch>>{

  private unprocessedDocuments: UnprocessedDocuments;
  private batchDocuments: BatchDocuments;
  private unprocessedDocumentsQueue: UnprocessedDocumentsQueue;
  private batch!: Batch;
  private maxBatchSizeBytes: number;
  private maxBatchTimeMs: number;
  private messageWaitTime: number;
  private documentStoreAddress: string;

  constructor(
    unprocessedDocuments: UnprocessedDocuments,
    batchDocuments: BatchDocuments,
    unprocessedDocumentsQueue: UnprocessedDocumentsQueue,
    maxBatchSizeBytes: number,
    maxBatchTimeSeconds: number,
    messageWaitTime: number,
    documentStoreAddress: string
  ){
    this.unprocessedDocuments = unprocessedDocuments;
    this.batchDocuments = batchDocuments;
    this.unprocessedDocumentsQueue = unprocessedDocumentsQueue;
    this.maxBatchSizeBytes = maxBatchSizeBytes;
    this.maxBatchTimeMs = maxBatchTimeSeconds * 1000;
    this.documentStoreAddress = documentStoreAddress;
    if(1 <= messageWaitTime && messageWaitTime <= 20){
      this.messageWaitTime = messageWaitTime;
    }else{
      throw Error('messageWaitTime must be >= 1 <=20');
    }
  }

  complete(batch: Batch){
    const timeComplete = (Date.now() - batch.creationTimestampMs) >= this.maxBatchTimeMs;
    const sizeComplete = batch.size() >= this.maxBatchSizeBytes;
    return timeComplete || sizeComplete;
  }

  async getNextDocumentPutEvent(){
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
    if(version === constants.OPEN_ATTESTATION_VERSION_ID_V2_FRAMEWORK){
      return document?.issuers?.[0]?.documentStore;
    }else if(version === constants.OPEN_ATTESTATION_VERSION_ID_V3_FRAMEWORK){
      return document?.proof?.method===constants.DOCUMENT_STORE_PROOF_TYPE?document.proof.value: undefined;
    }
  }

  getDocumentVersion(document: any): SchemaId.v2|SchemaId.v3|undefined{
    switch(document.version){
      case constants.OPEN_ATTESTATION_VERSION_ID_V2_FRAMEWORK:
      case constants.OPEN_ATTESTATION_VERSION_ID_V2_SHORT:
        return SchemaId.v2;
      case constants.OPEN_ATTESTATION_VERSION_ID_V3_FRAMEWORK:
      case constants.OPEN_ATTESTATION_VERSION_ID_V3_SHORT:
        return SchemaId.v3;
    }
  }

  verifyDocumentData(document: any): boolean{
    // validating schema of the document
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

  async next(){
    logger.debug('getting an event from the queue')
    // get the ObjectCreated:Put event from the unprocessed bucket
    const event = await this.getNextDocumentPutEvent();
    if(!event){
      logger.debug('no event in the queue')
      return;
    }
    //parsing the object
    logger.debug('event found, getting and parsing a document from the event')
    const s3Object = event.Body.Records[0].s3.object;
    const documentObject = await this.unprocessedDocuments.get({Key: s3Object.key});
    const documentStringBody = documentObject.Body!.toString();
    const documentJSONBody = JSON.parse(documentStringBody);
    logger.debug(documentJSONBody);

    // validating the document before adding it to batch
    logger.debug('verifying document data')
    if(this.verifyDocumentData(documentJSONBody)){
      // move the document from unprocessed bucket to batch bucket
      logger.debug('schema is valid, moving the document from unprocessed to batch bucket')
      await this.batchDocuments.put({Key: s3Object.key, Body: documentStringBody});
      await this.unprocessedDocuments.delete({Key: s3Object.key});

      // save the document into batch
      logger.debug('adding the document to the batch')
      this.batch.unwrappedDocuments.set(s3Object.key, {
        size: s3Object.size,
        body: documentJSONBody
      });
    }else{
      logger.debug('schema is invalid, the document will not be added to the batch');
    }
    // deleting the event after it processed
    logger.debug('deleting the event from the queue')
    await this.unprocessedDocumentsQueue.delete({ReceiptHandle: event.ReceiptHandle});
  }

  async start(): Promise<Batch>{
    // create new batch object
    this.batch = new Batch();
    logger.debug('created a new batch');
    // check should this batch be sent for wrapping or not
    while(!this.complete(this.batch)){
      await this.next();
    }
    return this.batch;
  }
}


class WrapBatch implements Task<void>{
  async start(){

  }
  async next(){

  }
}


class IssueBatch implements Task<void>{
  async start(){

  }
  async next(){

  }
}


class ProcessDocuments implements Task<void>{

  async start(){

  }

  async next(){

  }
}


export {
  ComposeBatch,
  WrapBatch,
  IssueBatch,
  ProcessDocuments
}
