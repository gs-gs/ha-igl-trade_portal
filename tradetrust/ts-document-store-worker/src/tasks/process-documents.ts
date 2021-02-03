import { DocumentStore } from "@govtechsg/document-store/src/contracts/DocumentStore";
import { Wallet } from "ethers";
import {
  BatchDocuments,
  IssuedDocuments,
  UnprocessedDocuments,
  UnprocessedDocumentsQueue
} from "../repos";
import { logger } from '../logger';
import ComposeBatch from "./compose-batch";
import { Batch } from './data';
import { Task } from "./interfaces";
import IssueBatch from "./issue-batch";
import SaveIssuedBatch from "./save-issued-batch";
import WrapBatch from "./wrap-batch";

interface IProcessDocumentsSettings{
  unprocessedDocuments: UnprocessedDocuments,
  batchDocuments: BatchDocuments,
  issuedDocuments: IssuedDocuments,
  unprocessedDocumentsQueue: UnprocessedDocumentsQueue,
  wallet: Wallet,
  documentStore: DocumentStore,
  messageWaitTime: number,
  messageVisibilityTimeout: number,
  batchSizeBytes: number,
  batchTimeSeconds: number,
  transactionTimeoutSeconds: number,
  transactionConfirmationThreshold: number,
  gasPriceMultiplier: number
  gasPriceLimitGwei: number,
  issueAttempts: number
  issueAttemptsIntervalSeconds: number,
  saveAttempts: number,
  saveAttemptsIntervalSeconds: number
}


class ProcessDocuments implements Task<void>{
  constructor(private settings: IProcessDocumentsSettings){}

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
    await new ComposeBatch({
      unprocessedDocuments: this.settings.unprocessedDocuments,
      batchDocuments: this.settings.batchDocuments,
      unprocessedDocumentsQueue: this.settings.unprocessedDocumentsQueue,
      batchSizeBytes: this.settings.batchSizeBytes,
      batchTimeSeconds: this.settings.batchTimeSeconds,
      messageWaitTime: this.settings.messageWaitTime,
      messageVisibilityTimeout: this.settings.messageVisibilityTimeout,
      documentStoreAddress: this.settings.documentStore.address,
      batch
    }).start()
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
    new WrapBatch({batch}).start()
    if(!batch.wrapped){
      logger.error('WrapBatch task failed');
      return;
    }


    logger.info('IssueBatch task started');
    await new IssueBatch({
      wallet: this.settings.wallet,
      documentStore: this.settings.documentStore,
      gasPriceLimitGwei: this.settings.gasPriceLimitGwei,
      gasPriceMultiplier: this.settings.gasPriceMultiplier,
      transactionTimeoutSeconds: this.settings.transactionTimeoutSeconds,
      transactionConfirmationThreshold: this.settings.transactionConfirmationThreshold,
      attempts: this.settings.issueAttempts,
      attemptsIntervalSeconds: this.settings.issueAttemptsIntervalSeconds,
      batch
    }).start()
    if(!batch.issued){
      logger.error('WrapBatch task failed');
      return;
    }


    logger.info('SaveIssuedBatch task started');
    await new SaveIssuedBatch({
      issuedDocuments: this.settings.issuedDocuments,
      batchDocuments: this.settings.batchDocuments,
      attempts: this.settings.saveAttempts,
      attemptsIntervalSeconds: this.settings.saveAttemptsIntervalSeconds,
      batch
    }).start()
    if(!batch.saved){
      logger.error('SaveIssuedBatch task failed');
      return;
    }
  }
}

export default ProcessDocuments;
