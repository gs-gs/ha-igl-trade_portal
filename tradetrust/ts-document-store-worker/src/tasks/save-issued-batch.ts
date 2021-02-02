import { logger } from 'src/logger';
import { BatchDocuments, IssuedDocuments } from "src/repos";
import { Batch } from './data';
import { Task } from './interfaces';


class SaveIssuedBatch implements Task<void>{
  constructor(
    private issuedDocuments: IssuedDocuments,
    private batchDocuments: BatchDocuments,
    private batch: Batch,
    private maxAttempts: number = 10,
    private attemptsIntervalSeconds: number = 60
  ){}
  async next(){
    for(let [key, document] of this.batch.wrappedDocuments){
      logger.info('Saving document "%s"...', key);
      const documentBodyString = JSON.stringify(document);
      await this.issuedDocuments.put({Key:key, Body: documentBodyString});
      logger.info('Document saved');
      try{
        await this.batchDocuments.delete({Key:key});
      }catch(e){
        if(e.code === 'NoSuchKey'){
          logger.warn('Failed to delete %s because it is already deleted', key);
          continue;
        }
        throw e;
      }
      logger.info('Deleted from batch backup');
    }
  }

  async start(){
    logger.info('Started saving issued batch documents...')
    this.batch.saved = false;
    for(let attempt = 0; attempt < this.maxAttempts; attempt++){
      try{
        logger.info('Attempt %s/%s', attempt, this.maxAttempts);
        await this.next();
        this.batch.saved = true;
        logger.info('Issued batch documents saved');
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
