import {
  SchemaId
} from '@govtechsg/open-attestation';
import {
  Bucket,
  Queue
} from '../repos';
import {
  OPEN_ATTESTATION_VERSION_ID_V2_SHORT,
  OPEN_ATTESTATION_VERSION_ID_V3_SHORT,
  DOCUMENT_STORE_PROOF_TYPE
} from '../constants';
import { logger } from '../logger';
import { Batch } from './data';
import { Task } from './interfaces';
import { RetryError } from './errors';


class InvalidEventError extends Error{}


class InvalidDocumentError extends Error{}


interface IComposeBatchProps{
  unprocessedDocuments: Bucket,
  batchDocuments: Bucket,
  unprocessedDocumentsQueue: Queue,
  batchTimeSeconds: number,
  batchSizeBytes: number,
  messageWaitTime: number,
  messageVisibilityTimeout: number,
  documentStoreAddress: string,
  batch: Batch,
  attempts?: number,
  attemptsIntervalSeconds?: number
}


interface IComposeBatchState{
  attempt: number
}

interface Document{
  key: string,
  size: number,
  body: {
    string: string,
    json: any
  }
}


abstract class ComposeBatch implements Task<void>{

  protected props: IComposeBatchProps;
  protected state: IComposeBatchState;

  constructor(props:IComposeBatchProps){
    this.props = Object.assign(props);
    this.props.attempts = this.props.attempts??10;
    this.props.attemptsIntervalSeconds = this.props.attemptsIntervalSeconds??60;
    this.state = {
      attempt: 0
    }
  }

  async getRawDocumentPutEvent(){
    let event;
    try{
      event = await this.props.unprocessedDocumentsQueue.get({
        VisibilityTimeout: this.props.messageVisibilityTimeout,
        WaitTimeSeconds: this.props.messageWaitTime
      });
    }catch(e){
      throw new RetryError(e);
    }
    return event;
  }


  parseDocumentPutEvent(event: any){
    try{
      event.Body = JSON.parse(event.Body);
    }catch(e){
      throw new InvalidEventError('Expected event.Body to be a valid JSON');
    }
    const records = event.Body.Records;
    if(records.length == 0 || records.length > 1){
      throw new InvalidEventError(`Expected event.Body.Records.length == 1, got: ${records.length}`);
    }
    const eventName = event.Body.Records[0].eventName;
    if(eventName !== 'ObjectCreated:Put'){
      throw new InvalidEventError(`Expected event.Body.Records[0].eventName == "ObjectCreated:Put", got: "${eventName}"`);
    }
    return event;
  }


  async deleteEvent(event: any){
    try{
      await this.props.unprocessedDocumentsQueue.delete({ReceiptHandle: event.ReceiptHandle})
    }catch(e){
      throw new RetryError(e);
    }
  }


  async getDocumentDataFromEvent(event: any): Promise<Document|undefined>{
    logger.debug('getDocumentDataFromEvent');
    const s3Object = event.Body.Records[0].s3.object;
    let documentObject;
    try{
      logger.info('Trying do download the document. Key "%s", eTag "%s"', s3Object.key, s3Object.eTag);
      documentObject = await this.props.unprocessedDocuments.get({Key: s3Object.key, IfMatch: s3Object.eTag});
    }catch(e){
      // these conditions are separate just for verbosity
      if(e.code === 'NoSuchKey'){
        logger.warn('Document not found');
        return undefined;
      }else if(e.code === 'PreconditionFailed'){
        logger.warn('Document with a matching eTag not found');
        return undefined;
      }
      throw new RetryError(e);
    }
    const documentStringBody = documentObject.Body!.toString();
    // the only potential error here is invalid JSON string
    try{
      const documentJSONBody = JSON.parse(documentStringBody);
      documentObject = {
        key: s3Object.key,
        size: s3Object.size,
        body: {
          string: documentStringBody,
          json: documentJSONBody
        }
      }
      logger.info('Downloaded');
      return documentObject;
    }catch(e){
      throw new InvalidDocumentError('Document body is not a valid JSON');
    }
  }


  getDocumentStoreAddress(document: Document, version: SchemaId.v2|SchemaId.v3|undefined): string|undefined{
    logger.debug('getDocumentStoreAddress');
    if(version === SchemaId.v2){
      return document.body.json.issuers?.[0]?.documentStore;
    }else if(version === SchemaId.v3){
      return document.body.json.proof?.method===DOCUMENT_STORE_PROOF_TYPE?document.body.json.proof.value: undefined;
    }
    return undefined;
  }


  getDocumentVersion(document: Document): SchemaId.v2|SchemaId.v3|undefined{
    logger.debug('getDocumentVersion');
    switch(document.body.json.version){
      case SchemaId.v2:
      case OPEN_ATTESTATION_VERSION_ID_V2_SHORT:
        return SchemaId.v2;
      case SchemaId.v3:
      case OPEN_ATTESTATION_VERSION_ID_V3_SHORT:
        return SchemaId.v3;
    }
  }


  async putDocumentToBatchBackup(document: Document){
    logger.debug('putDocumentToBatchBackup');
    try{
      logger.info('Adding document "%s" to backup', document.key);
      await this.props.batchDocuments.put({Key: document.key, Body: document.body.string});
      logger.info('Added');
    }catch(e){
      throw new RetryError(e);
    }
  }

  async removeDocumentFromUnprocessed(document: Document){
    logger.debug('removeDocumentFromUnprocessed');
    try{
      logger.info('Deleting document "%s" from unprocessed', document.key);
      await this.props.unprocessedDocuments.delete({Key: document.key});
      logger.info('Deleted');
    }catch(e){
      throw new RetryError(e);
    }
  }

  async addUnwrappedDocumentToBatch(document: Document){
    logger.debug('addDocumentToBatch')
    await this.putDocumentToBatchBackup(document);
    await this.removeDocumentFromUnprocessed(document);
    this.props.batch.unwrappedDocuments.set(document.key, {
      size: document.size,
      body: document.body.json
    });
  }

  async addWrappedDocumentToBatch(document: Document){
    logger.debug('addDocumentToBatch')
    await this.putDocumentToBatchBackup(document);
    await this.removeDocumentFromUnprocessed(document);
    this.props.batch.unwrappedDocuments.set(document.key, {
      size: document.size,
      body: document.body.json
    });
  }

  async start(){
    logger.info('Starting batch composition');
    // if batch didn't get any documents from RestoreBatch task
    // batch.compositionStartTimestamp will be reset and time spent on RestoreBatch task will be skipped
    if(!this.props.batch.restored){
      this.props.batch.compositionStartTimestamp = Date.now();
    }
    while(!this.props.batch.composed){
      try{
        await this.next();
        if(this.state.attempt > 0){
          logger.info('Reseting attempts after succesful iteration');
          this.state.attempt = 0;
        }
      }catch(e){
        if(e instanceof RetryError){
          this.state.attempt++;
          if(this.state.attempt < this.props.attempts!){
            logger.error(e.source);
            logger.info('An unexpected error happened, waiting %s seconds and retrying', this.props.attemptsIntervalSeconds);
            await new Promise(r=>setTimeout(r, this.props.attemptsIntervalSeconds! * 1000));
          }else{
            logger.error('Ran out of attempts');
            throw e.source;
          }

        }else{
          throw e;
        }
      }
      this.props.batch.composed = this.props.batch.isComposed(this.props.batchSizeBytes, this.props.batchTimeSeconds)
    }
  }

  async next(){
    // Getting the next event and reacting on all potential errors
    let event = await this.getRawDocumentPutEvent();
    // if no event received, exit
    if(!event){
      return;
    }
    try{
      event = this.parseDocumentPutEvent(event);
    }catch(e){
      if(e instanceof InvalidEventError){
        logger.error(e);
        logger.info('Deleting the invalid event');
        await this.deleteEvent(event);
        logger.info('Deleted');
        return;
      }else{
        throw e;
      }
    }
    // Getting document data and reacting on errors
    try{
      const document = await this.getDocumentDataFromEvent(event);
      if(!document){
        logger.warn('Document not found, deleting event');
      }else{
        await this.verifyDocument(document);
        await this.addDocumentToBatch(document);
        logger.info('Document succesfully added, deleting event');
      }
      await this.deleteEvent(event);
      logger.info('Deleted');
    }catch(e){
      if(e instanceof InvalidDocumentError){
        logger.error(e);
        logger.info('Deleting the invalid document event');
        await this.deleteEvent(event);
        logger.info('Deleted');
      }else{
        throw e;
      }
    }
  }

  abstract verifyDocument(document: Document): Promise<void>;
  abstract addDocumentToBatch(document: Document): Promise<void>;

}

export {
  ComposeBatch,
  IComposeBatchProps,
  IComposeBatchState,
  InvalidEventError,
  InvalidDocumentError,
  Document
}

export default ComposeBatch;
