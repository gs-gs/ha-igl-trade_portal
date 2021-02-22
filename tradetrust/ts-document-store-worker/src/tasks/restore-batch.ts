import {
  Bucket,
} from '../repos';
import { logger } from '../logger';
import { Batch } from './data';
import { Task } from './interfaces';
import { RetryError } from './errors';


interface IRestoreBatchProps{
  batchDocuments: Bucket,
  batch: Batch,
  batchSizeBytes: number,
  batchTimeSeconds: number,
  attempts?: number,
  attemptsIntervalSeconds?: number
}

interface IRestoreBatchState{
  attempt: number
}


class RestoreBatch implements Task<Promise<void>>{

  private props: IRestoreBatchProps;
  private state: IRestoreBatchState;

  constructor(props: IRestoreBatchProps){
    this.props = props;
    this.props.attempts = this.props.attempts??10;
    this.props.attemptsIntervalSeconds = this.props.attemptsIntervalSeconds??60;
    this.state = {
      attempt: 0
    }
  }

  async start(){
    while(true){
      try{
        await this.next();
        break;
      }catch(e){
        // increasing attempt index
        this.state.attempt++;
        if(e instanceof RetryError){
          logger.error(e.source);
          if(this.state.attempt < this.props.attempts!){
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
    }
  }

  async listBatchBackupDocuments(ContinuationToken: string|undefined){
    try{
      return await this.props.batchDocuments.list({ContinuationToken});
    }catch(e){
      throw new RetryError(e);
    }
  }

  async next(){
    logger.info('Starting batch restoration process');
    logger.info('Attempt %s/%s', this.state.attempt + 1, this.props.attempts);
    let ContinuationToken: string|undefined;
    this.props.batch.compositionStartTimestamp = Date.now();
    logger.info('Composition start timestamp = %s', this.props.batch.compositionStartTimestamp);
    do{
      const listObjectsResponse = await this.listBatchBackupDocuments(ContinuationToken);
      ContinuationToken = listObjectsResponse.ContinuationToken;
      for(let s3Object of listObjectsResponse.Contents??[]){
        if(!this.props.batch.unwrappedDocuments.has(s3Object.Key!)){

          let documentObject;
          try{
             documentObject = await this.props.batchDocuments.get({Key: s3Object.Key!});
          }catch(e){
            if(e.code == 'NoSuchKey'){
              logger.error('Document "%s" got deleted before it was added into the batch during restoration.', s3Object.Key);
              continue;
            }else{
              throw new RetryError(e);
            }
          }

          let documentJSONBody;
          try{
            documentJSONBody = JSON.parse(documentObject.Body!.toString());
          }catch(e){
            logger.error('Document "%s" is not a valid JSON', s3Object.Key);
            continue;
          }

          this.props.batch.unwrappedDocuments.set(s3Object.Key!, {body: documentJSONBody, size: s3Object.Size!});
          logger.info('Document "%s" added to the batch', s3Object.Key);
        }else{
          logger.info('Document "%s" already added', s3Object.Key);
        }
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

    this.props.batch.restored = this.props.batch.unwrappedDocuments.size > 0;
    logger.info(
      'The batch restoration process is completed. The batch final state %o',
      {restored: this.props.batch.restored, composed: this.props.batch.composed}
    );

  }
}

export default RestoreBatch;
