import { logger } from 'src/logger';
import { BatchDocuments, IssuedDocuments } from "src/repos";
import { Batch } from './data';
import { Task } from './interfaces';


class SaveIssuedBatch implements Task<void>{
  constructor(
    private issuedDocuments: IssuedDocuments,
    private batchDocuments: BatchDocuments,
    private batch: Batch
  ){}
  async next(){
    for(let [key, document] of this.batch.wrappedDocuments){
      logger.info('Saving document "%s"...', key);
      const documentBodyString = JSON.stringify(document);
      await this.issuedDocuments.put({Key:key, Body: documentBodyString});
      logger.info('Document saved');
      await this.batchDocuments.delete({Key:key});
      logger.info('Deleted from batch backup');
    }
  }

  async start(){
    logger.info('Started saving issued batch documents...')
    await this.next();
    logger.info('Issued batch documents saved');
  }

}

export default SaveIssuedBatch;
