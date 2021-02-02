import { DocumentStore } from "@govtechsg/document-store/src/contracts/DocumentStore";
import { Wallet } from "ethers";
import {
  BatchDocuments,
  IssuedDocuments,
  UnprocessedDocuments,
  UnprocessedDocumentsQueue
} from "src/repos";
import { logger } from 'src/logger';
import ComposeBatch from "./compose-batch";
import { Batch } from './data';
import { Task } from "./interfaces";
import IssueBatch from "./issue-batch";
import SaveIssuedBatch from "./save-issued-batch";
import WrapBatch from "./wrap-batch";


class ProcessDocuments implements Task<void>{
  constructor(
    private unprocessedDocuments: UnprocessedDocuments,
    private batchDocuments: BatchDocuments,
    private issuedDocuments: IssuedDocuments,
    private unprocessedDocumentsQueue: UnprocessedDocumentsQueue,
    private wallet: Wallet,
    private documentStore: DocumentStore,
    private messageWaitTime: number,
    private messageVisibilityTimeout: number,
    private maxBatchSizeBytes: number,
    private maxBatchTimeSeconds: number,
    private transactionTimeoutSeconds: number,
    private transactionConfirmationThreshold: number,
    private gasPriceMultiplier: number
  ){}

  /* istanbul ignore next */
  async start(){
    logger.debug('start')
    while(true){
      await this.next();
    }
  }

  async next(){
    logger.debug('next');
    const batch = new Batch();
    logger.info('A new batch created');
    logger.info('ComposeBatch task started');
    await new ComposeBatch(
      this.unprocessedDocuments,
      this.batchDocuments,
      this.unprocessedDocumentsQueue,
      this.maxBatchTimeSeconds,
      this.maxBatchSizeBytes,
      this.messageWaitTime,
      this.messageVisibilityTimeout,
      this.documentStore.address,
      batch
    ).start()
    logger.debug('batch.isEmpty')
    if(!batch.composed){
      logger.error('ComposeBatch task failed');
      return;
    }
    if(batch.isEmpty()){
      logger.info('The batch is empty, skipping further steps');
      return;
    }


    logger.info('WrapBatch task started');
    new WrapBatch(batch).start()
    if(!batch.wrapped){
      logger.error('WrapBatch task failed');
      return;
    }


    logger.info('IssueBatch task started');
    await new IssueBatch(
      this.wallet,
      this.documentStore,
      batch,
      this.gasPriceMultiplier,
      this.transactionConfirmationThreshold,
      this.transactionTimeoutSeconds
    ).start()
    if(!batch.issued){
      logger.error('WrapBatch task failed');
      return;
    }


    logger.info('SaveIssuedBatch task started');
    await new SaveIssuedBatch(
      this.issuedDocuments,
      this.batchDocuments,
      batch
    ).start()
    if(!batch.saved){
      logger.error('SaveIssuedBatch task failed');
      return;
    }
  }
}

export default ProcessDocuments;
