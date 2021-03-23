import { logger } from '../logger';
import { Bucket } from "../repos";
import { Batch } from './data';
import { Task } from './interfaces';
import { RetryError } from './errors';


interface ISaveBatchProps{
  processedDocuments: Bucket,
  batchDocuments: Bucket,
  batch: Batch,
  attempts?: number,
  attemptsIntervalSeconds?: number
}

interface ISaveBatchState{
  attempt: number,
  savedDocuments: Array<string>
  deletedDocuments: Array<string>
}


class SaveBatch implements Task<void>{

  private props: ISaveBatchProps;
  private state: ISaveBatchState;

  constructor(props: ISaveBatchProps){
    this.props = Object.assign(props);
    this.props.attempts = this.props.attempts??10;
    this.props.attemptsIntervalSeconds = this.props.attemptsIntervalSeconds??60;
    this.state = {
      attempt: 0,
      savedDocuments: new Array<string>(),
      deletedDocuments: new Array<string>()
    }
  }

  async saveDocument(key: string, body: any){
    if(this.state.savedDocuments.includes(key)){
      logger.debug('"%s" already saved', key);
      return;
    }
    logger.info('Saving "%s" to processed batch documents', key);
    const documentBodyString = JSON.stringify(body);
    try{
      await this.props.processedDocuments.put({Key:key, Body: documentBodyString});
    }catch(e){
      throw new RetryError(e);
    }
    this.state.savedDocuments.push(key);
    logger.info('Saved');
  }

  async deleteDocument(key: string){
    if(this.state.deletedDocuments.includes(key)){
      logger.debug('"%s" already deleted', key);
      return;
    }
    try{
      logger.info('Deleting "%s" from batch backup documents', key);
      await this.props.batchDocuments.delete({Key:key});
      this.state.deletedDocuments.push(key);
      logger.info('Deleted');
    }catch(e){
      if(e.code === 'NoSuchKey'){
        this.state.deletedDocuments.push(key);
        logger.warn('Failed to delete because it is already deleted');
        return;
      }
      throw new RetryError(e);
    }
  }

  async saveBatch(){
    for(let [key, document] of this.props.batch.wrappedDocuments){
      // only reason to fail is unexpected error that will prevent deletion without saving
      await this.saveDocument(key, document.body);
      await this.deleteDocument(key);
    }
  }

  async start(){
    logger.info('SaveBatch task started');
    // saving keys of already saved & deleted documents to restore state after a critical unexpected error
    this.state.savedDocuments = new Array<string>();
    this.state.deletedDocuments = new Array<string>();
    while(true){
      try{
        logger.info('Attempt %s/%s', this.state.attempt + 1, this.props.attempts);
        await this.saveBatch();
        logger.info('Processed batch documents saved');
        return;
      }catch(e){
        if(e instanceof RetryError){
          this.state.attempt++;
          if(this.state.attempt < this.props.attempts!){
            logger.warn('An unexpected error occured');
            logger.warn('Reason:', e.source);
            logger.warn('Waiting %s seconds', this.props.attemptsIntervalSeconds);
            await new Promise(resolve=>setTimeout(resolve, this.props.attemptsIntervalSeconds! * 1000));
          }else{
            logger.error('Ran out of attempts. Reason:', e.source);
            throw e.source;
          }
        }
        else{
          throw e;
        }
      }
    }
  }

}

export default SaveBatch;
