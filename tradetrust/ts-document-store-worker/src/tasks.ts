import pino from 'pino';
import { Wallet } from 'ethers';
import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import { validateSchema, verifySignature, wrapDocuments, wrapDocument, SchemaId } from '@govtechsg/open-attestation';
import {
  connectDocumentStore
} from './document-store';
import {
  UnprocessedDocuments,
  BatchDocuments,
  IssuedDocuments,
  UnprocessedDocumentsQueue
} from './repos';
import constants from './constants';
import { utils } from 'ethers';



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
  wrappedDocuments: Map<string, any>;
  merkleRoot: string = '';

  constructor(){
    this.creationTimestampMs = Date.now();
    this.unwrappedDocuments = new Map<string, UnwrappedDocument>();
    this.wrappedDocuments = new Map<string, any>();
  }

  size(): number{
    let size = 0;
    this.unwrappedDocuments.forEach(document=>{size += document.size});
    return size;
  }

}

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
  constructor(private batch: Batch){}

  prepareBatchUnwrappedDocumentsData(){
    const keys:Array<string> = new Array<string>(this.batch.unwrappedDocuments.size);
    const bodies: Array<any> = new Array<any>(this.batch.unwrappedDocuments.size);
    let documentIndex = 0;
    for(let [key, entry] of this.batch.unwrappedDocuments){
      keys[documentIndex] = key;
      bodies[documentIndex] = entry.body;
      documentIndex++;
    }
    return {keys, bodies};
  }

  next(){
    let {keys, bodies} = this.prepareBatchUnwrappedDocumentsData();
    bodies = wrapDocuments(bodies);
    keys.forEach((key, index)=>{this.batch.wrappedDocuments.set(key, bodies[index])});
    this.batch.merkleRoot = bodies[0].signature.merkleRoot;
  }

  start(){
    this.next();
  }
}

// TODO: add gas price updates
// TODO: add stuck transaction handling
class IssueBatch implements Task<void>{

  constructor(
    private wallet: Wallet,
    private documentStore: DocumentStore,
    private batch: Batch
  ){}

  async next(): Promise<boolean>{
    const gasLimit = 1000000;
    const gasPrice = await this.wallet.getGasPrice();
    const nonce = await this.wallet.getTransactionCount('latest');
    const merkleRoot = '0x'+this.batch.merkleRoot;

    const transaction = await this.documentStore.populateTransaction.issue(merkleRoot, {nonce, gasPrice, gasLimit});
    const transactionResponse = await this.wallet.sendTransaction(transaction);
    const transactionReceipt = await transactionResponse.wait();
    return true;
  }

  async start(){
    while(!await this.next()){
      // update gas price code goes here
    }
  }
}

class SaveIssuedBatch implements Task<void>{
  constructor(
    private issuedDocuments: IssuedDocuments,
    private batchDocuments: BatchDocuments,
    private batch: Batch
  ){}
  async next(){
    for(let [key, document] of this.batch.wrappedDocuments){
      const documentBodyString = JSON.stringify(document);
      await this.issuedDocuments.put({Key:key, Body: documentBodyString});
      await this.batchDocuments.delete({Key:key})
    }
  }

  async start(){
    await this.next();
  }

}


class ProcessDocuments implements Task<void>{
  constructor(
    private unprocessedDocuments: UnprocessedDocuments,
    private batchDocuments: BatchDocuments,
    private issuedDocuments: IssuedDocuments,
    private unprocessedDocumentsQueue: UnprocessedDocumentsQueue,
    private wallet: Wallet,
    private documentStore: DocumentStore,
    private messageWaitTime: number,
    private maxBatchSizeBytes: number,
    private maxBatchTimeSeconds: number
  ){}

  async start(){
    while(true){
      await this.next();
    }
  }

  async next(){
    const batch = await new ComposeBatch(
      this.unprocessedDocuments,
      this.batchDocuments,
      this.unprocessedDocumentsQueue,
      this.maxBatchSizeBytes,
      this.maxBatchTimeSeconds,
      this.messageWaitTime,
      this.documentStore.address
    ).start()
    new WrapBatch(batch).start()
    await new IssueBatch(
      this.wallet,
      this.documentStore,
      batch
    ).start()
    await new SaveIssuedBatch(
      this.issuedDocuments,
      this.batchDocuments,
      batch
    ).start()
  }
}


export {
  Batch,
  ComposeBatch,
  WrapBatch,
  IssueBatch,
  ProcessDocuments
}
