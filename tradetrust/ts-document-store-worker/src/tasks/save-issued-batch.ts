import { logger } from '../logger';
import { BatchDocuments, IssuedDocuments } from "../repos";
import { Batch } from './data';
import { Task } from './interfaces';


class SaveIssuedBatch implements Task<void>{

  private issuedDocuments: IssuedDocuments;
  private batchDocuments: BatchDocuments;
  private batch: Batch;
  private attempts: number;
  private attemptsIntervalSeconds: number;

  private savedDocuments!: Array<string>;
  private deletedDocuments!: Array<string>;

  constructor({
    issuedDocuments,
    batchDocuments,
    batch,
    attempts = 10,
    attemptsIntervalSeconds = 60
  }:{
    issuedDocuments: IssuedDocuments,
    batchDocuments: BatchDocuments,
    batch: Batch,
    attempts?: number,
    attemptsIntervalSeconds?: number
  }){
    this.issuedDocuments = issuedDocuments;
    this.batchDocuments = batchDocuments;
    this.batch = batch;
    this.attempts = attempts;
    this.attemptsIntervalSeconds = attemptsIntervalSeconds;
  }

  async saveDocument(key: string, body: any){
    if(this.savedDocuments.includes(key)){
      logger.debug('"%s" already saved', key);
      return;
    }
    logger.info('Saving "%s" to issued batch documents', key);
    const documentBodyString = JSON.stringify(body);
    await this.issuedDocuments.put({Key:key, Body: documentBodyString});
    this.savedDocuments.push(key);
    logger.info('Saved');
  }

  async deletedDocument(key: string){
    if(this.deletedDocuments.includes(key)){
      logger.debug('"%s" already deleted', key);
      return;
    }
    try{
      logger.info('Deleting "%s" from batch backup documents', key);
      await this.batchDocuments.delete({Key:key});
      this.deletedDocuments.push(key);
      logger.info('Deleted');
    }catch(e){
      if(e.code === 'NoSuchKey'){
        this.deletedDocuments.push(key);
        logger.warn('Failed to delete because it is already deleted');
        return;
      }
      throw e;
    }
  }

  async next(){
    for(let [key, document] of this.batch.wrappedDocuments){
      // only reason to fail is unexpected error that will prevent deletion without saving
      await this.saveDocument(key, document);
      await this.deletedDocument(key);
    }
  }

  async start(){
    logger.info('Started saving issued batch documents...')
    this.batch.saved = false;
    // saving keys of already saved & deleted documents to restore state after a critical unexpected error
    this.deletedDocuments = new Array<string>();
    this.savedDocuments = new Array<string>();
    for(let attempt = 0; attempt < this.attempts; attempt++){
      try{
        logger.info('Attempt %s/%s', attempt + 1, this.attempts);
        await this.next();
        this.batch.saved = true;
        logger.info('Issued batch documents saved');
        return;
      }catch(e){
        logger.error('An unexpected error occured');
        logger.error(e);
        logger.info('Waiting %s seconds', this.attemptsIntervalSeconds);
        await new Promise(resolve=>setTimeout(resolve, this.attemptsIntervalSeconds * 1000));
      }
    }
  }

}

export default SaveIssuedBatch;
