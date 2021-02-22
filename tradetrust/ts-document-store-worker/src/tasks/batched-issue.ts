import { DocumentStore } from "@govtechsg/document-store/src/contracts/DocumentStore";
import { Wallet } from "ethers";
import {
  BatchDocuments,
  IssuedDocuments,
  UnprocessedDocuments,
  UnprocessedDocumentsQueue
} from "../repos";
import { logger } from '../logger';
import RestoreBatch from "./restore-batch";
import ComposeBatch from "./compose-batch";
import { Batch } from './data';
import { Task } from "./interfaces";
import IssueBatch from "./issue-batch";
import SaveBatch from "./save-batch";
import WrapBatch from "./wrap-batch";

interface IProcessDocumentsProps{
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
  restoreAttempts: number,
  restoreAttemptsIntervalSeconds: number,
  composeAttempts: number,
  composeAttemptsIntervalSeconds: number,
  issueAttempts: number
  issueAttemptsIntervalSeconds: number,
  saveAttempts: number,
  saveAttemptsIntervalSeconds: number
}


class BatchedIssue implements Task<void>{
  private props: IProcessDocumentsProps;

  constructor(props: IProcessDocumentsProps){
    this.props = props;
  }

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


    logger.info('RestoreBatch task started');
    await new RestoreBatch({
      batchDocuments: this.props.batchDocuments,
      batchTimeSeconds: this.props.batchTimeSeconds,
      batchSizeBytes: this.props.batchSizeBytes,
      attempts: this.props.restoreAttempts,
      attemptsIntervalSeconds: this.props.restoreAttemptsIntervalSeconds,
      batch
    }).start();


    logger.info('ComposeBatch task started');
    await new ComposeBatch({
      unprocessedDocuments: this.props.unprocessedDocuments,
      batchDocuments: this.props.batchDocuments,
      unprocessedDocumentsQueue: this.props.unprocessedDocumentsQueue,
      batchSizeBytes: this.props.batchSizeBytes,
      batchTimeSeconds: this.props.batchTimeSeconds,
      messageWaitTime: this.props.messageWaitTime,
      messageVisibilityTimeout: this.props.messageVisibilityTimeout,
      documentStoreAddress: this.props.documentStore.address,
      attempts: this.props.composeAttempts,
      attemptsIntervalSeconds: this.props.composeAttemptsIntervalSeconds,
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
      wallet: this.props.wallet,
      documentStore: this.props.documentStore,
      gasPriceLimitGwei: this.props.gasPriceLimitGwei,
      gasPriceMultiplier: this.props.gasPriceMultiplier,
      transactionTimeoutSeconds: this.props.transactionTimeoutSeconds,
      transactionConfirmationThreshold: this.props.transactionConfirmationThreshold,
      attempts: this.props.issueAttempts,
      attemptsIntervalSeconds: this.props.issueAttemptsIntervalSeconds,
      batch
    }).start()
    if(!batch.issued){
      logger.error('WrapBatch task failed');
      return;
    }


    logger.info('SaveIssuedBatch task started');
    await new SaveBatch({
      issuedDocuments: this.props.issuedDocuments,
      batchDocuments: this.props.batchDocuments,
      attempts: this.props.saveAttempts,
      attemptsIntervalSeconds: this.props.saveAttemptsIntervalSeconds,
      batch
    }).start()
    if(!batch.saved){
      logger.error('SaveIssuedBatch task failed');
      return;
    }
  }
}

export default BatchedIssue;
