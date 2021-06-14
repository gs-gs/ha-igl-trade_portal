import { DocumentStore } from "@govtechsg/document-store/src/contracts/DocumentStore";
import { Wallet } from "ethers";
import {
  InvalidDocuments,
  BatchDocuments,
  IssuedDocuments,
  UnprocessedDocuments,
  UnprocessedDocumentsQueue
} from "src/repos";
import { logger } from 'src/logger';
import RestoreBatch from "src/tasks/restore-batch";
import ComposeIssueBatch from "src/tasks/compose-issue-batch";
import { Batch } from 'src/tasks/data';
import { Task } from "src/tasks/interfaces";
import IssueBatch from "src/tasks/issue-batch";
import SaveBatch from "src/tasks/save-batch";
import WrapBatch from "src/tasks/wrap-batch";

interface IProcessDocumentsProps{
  invalidDocuments: InvalidDocuments,
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
    logger.info('BatchedIssue task started');
    while(true){
      try{
        await this.next();
      }catch(e){
        logger.error('An unexpected error occured. Reason:', e);
        // to not hang on endless cycle
        await new Promise(r=>setTimeout(r, 1000));
      }
    }
  }

  async next(){
    const batch = new Batch();

    await new RestoreBatch({
      wrapped: false,
      documentStore: this.props.documentStore,
      invalidDocuments: this.props.invalidDocuments,
      batchDocuments: this.props.batchDocuments,
      batchTimeSeconds: this.props.batchTimeSeconds,
      batchSizeBytes: this.props.batchSizeBytes,
      attempts: this.props.restoreAttempts,
      attemptsIntervalSeconds: this.props.restoreAttemptsIntervalSeconds,
      batch
    }).start();

    await new ComposeIssueBatch({
      invalidDocuments: this.props.invalidDocuments,
      unprocessedDocuments: this.props.unprocessedDocuments,
      batchDocuments: this.props.batchDocuments,
      unprocessedDocumentsQueue: this.props.unprocessedDocumentsQueue,
      batchSizeBytes: this.props.batchSizeBytes,
      batchTimeSeconds: this.props.batchTimeSeconds,
      messageWaitTime: this.props.messageWaitTime,
      messageVisibilityTimeout: this.props.messageVisibilityTimeout,
      wallet: this.props.wallet,
      documentStore: this.props.documentStore,
      attempts: this.props.composeAttempts,
      attemptsIntervalSeconds: this.props.composeAttemptsIntervalSeconds,
      batch
    }).start()
    if(batch.isEmpty()){
      logger.info('The batch is empty, skipping further steps');
      return;
    }

    new WrapBatch({batch}).start()

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

    await new SaveBatch({
      processedDocuments: this.props.issuedDocuments,
      batchDocuments: this.props.batchDocuments,
      attempts: this.props.saveAttempts,
      attemptsIntervalSeconds: this.props.saveAttemptsIntervalSeconds,
      batch
    }).start()
  }
}

export default BatchedIssue;
