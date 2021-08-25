import path from 'path';
import { S3 } from 'aws-sdk';
import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import {
  Bucket,
} from 'src/repos';
import { logger } from 'src/logger';
import { Batch } from './data';
import { Task } from './interfaces';
import { RetryError } from './errors';
import {
  VerifyDocument,
  VerifyDocumentIssuance,
  VerifyDocumentRevocation,
  VerificationError
} from 'src/tasks/utils/verify-document';


interface IRestoreBatchProps{
  wrapped: boolean,
  documentStore: DocumentStore,
  invalidDocuments: Bucket,
  batchDocuments: Bucket,
  batch: Batch,
  batchSizeBytes: number,
  batchTimeSeconds: number,
  attempts?: number,
  attemptsIntervalSeconds?: number
}

interface IRestoreBatchState{
  attempt: number,
  verificator: VerifyDocument,
  restoredDocuments: Map<string, any>
}


class RestoreBatch implements Task<Promise<void>>{

  private props: IRestoreBatchProps;
  private state: IRestoreBatchState;

  constructor(props: IRestoreBatchProps){
    this.props = props;
    this.props.attempts = this.props.attempts??10;
    this.props.attemptsIntervalSeconds = this.props.attemptsIntervalSeconds??60;
    const VerificatorClass = props.wrapped?VerifyDocumentRevocation:VerifyDocumentIssuance;
    this.state = {
      attempt: 0,
      restoredDocuments: props.wrapped?props.batch.wrappedDocuments:props.batch.unwrappedDocuments,
      verificator: new VerificatorClass({documentStore: props.documentStore})
    }
  }

  async start(){
    logger.info('RestoreBatch started');
    this.props.batch.compositionStartTimestamp = Date.now();
    logger.info('Composition start timestamp = %s', this.props.batch.compositionStartTimestamp);
    while(true){
      try{
        await this.restoreBatch();
        return;
      }catch(e){
        this.state.attempt++;
        if(e instanceof RetryError){
          if(this.state.attempt < this.props.attempts!){
            logger.warn('An unexpected error occured');
            logger.warn('Reason:', e.source);
            logger.warn('Waiting %s seconds', this.props.attemptsIntervalSeconds);
            await new Promise(r=>setTimeout(r, this.props.attemptsIntervalSeconds! * 1000));
          }else{
            logger.error('Ran out of attempts. Reason:', e.source);
            throw e.source;
          }
        }else{
          throw e;
        }
      }
    }
  }

  async listBatchBackupDocuments(ContinuationToken: string|undefined){
    try{
      return await this.props.batchDocuments.list({ContinuationToken});
    }catch(e){
      throw new RetryError(e);
    }
  }

  async deleteDocumentFromBackup(key: string){
    logger.info('Deleting document "%s" from backup', key);
    try{
      this.props.batchDocuments.delete({Key: key});
    }catch(e){
      if(e.code === 'KeyError'){
        logger.warn('Document not exists');
      }else{
        throw new RetryError(e);
      }
    }
    logger.info('Deleted');
  }

  async putDocumentAndReasonToInvalid(key: string, body: string, e: VerificationError){
    try{
      logger.info('Adding document "%s" to invalid', key);
      await this.props.invalidDocuments.put({Key: key, Body: body});
      const parsedPath = path.parse(key);
      const reasonFilename = `${path.join(parsedPath.dir, parsedPath.name)}.reason.json`;
      const reasonBody = e.message??'Undefined';
      logger.info('Adding reason "%s" to invalid', reasonFilename);
      await this.props.invalidDocuments.put({
        Key: reasonFilename,
        Body: JSON.stringify({
          reason: reasonBody
        })
      });
    }catch(e){
      throw new RetryError(e);
    }
  }

  parseDocumentJSON(body: string){
    try{
      return JSON.parse(body);
    }catch(e){
      throw new VerificationError('Document is not a valid JSON');
    }
  }

  async addDocumentToRestoredDocuments(key: string, body: any, size: number){
    try{
      await this.state.verificator.verify(body);
      this.state.restoredDocuments.set(key, {body, size});
    }catch(e){
      if(e instanceof VerificationError){
        throw e;
      }else{
        throw new RetryError(e);
      }
    }
  }

  async getDocument(s3Object: S3.Object){
    logger.info('Downloading document "%s"', s3Object.Key);
    let documentObject;
    try{
       documentObject = await this.props.batchDocuments.get({Key: s3Object.Key!});
       logger.info('Downloaded');
       return {
         key: s3Object.Key!,
         size: s3Object.Size!,
         body: {
           string: documentObject.Body!.toString(),
           json: undefined
         }
       }
    }catch(e){
      if(e.code == 'NoSuchKey'){
        logger.error('Document "%s" was deleted before it was added into the batch during restoration.', s3Object.Key);
        return undefined;
      }else{
        throw new RetryError(e);
      }
    }
  }


  async restoreBatchDocument(s3Object: S3.Object){
    if(s3Object.Key && !this.state.restoredDocuments.has(s3Object.Key)){
      const document = await this.getDocument(s3Object);
      if(!document){
        return false;
      }
      try{
        document.body.json = this.parseDocumentJSON(document.body.string);
        await this.addDocumentToRestoredDocuments(
          document.key,
          document.body.json,
          document.size
        )
      }catch(e){
        if(e instanceof VerificationError){
          logger.warn('Document "%s" is invalid: %s', document.key, e.message);
          await this.deleteDocumentFromBackup(document.key);
          await this.putDocumentAndReasonToInvalid(document.key, document.body.string, e);
          return;
        }else{
          throw e;
        }
      }
      logger.info('Document "%s" added to the batch', document.key);
      return true;
    }else{
      logger.info('Document "%s" already added', s3Object.Key);
      return false;
    }
  }

  async restoreBatch(){
    logger.info('Attempt %s/%s', this.state.attempt + 1, this.props.attempts);
    let ContinuationToken: string|undefined;
    do{
      const listObjectsResponse = await this.listBatchBackupDocuments(ContinuationToken);
      ContinuationToken = listObjectsResponse.ContinuationToken;
      for(let s3Object of listObjectsResponse.Contents??[]){
        await this.restoreBatchDocument(s3Object);
        this.props.batch.composed = this.props.batch.isComposed(this.props.batchSizeBytes, this.props.batchTimeSeconds);
        if(this.props.batch.composed){
          break;
        }
        if(this.state.attempt > 0){
          logger.info('Reseting attempt index after a succesful iteration');
          this.state.attempt = 0;
        }
      }
    }while(ContinuationToken && !this.props.batch.composed);
    this.props.batch.restored = this.state.restoredDocuments.size > 0;
    logger.info(
      'The batch restoration process is completed. The batch final state %o',
      {restored: this.props.batch.restored, composed: this.props.batch.composed}
    );

  }
}

export default RestoreBatch;
