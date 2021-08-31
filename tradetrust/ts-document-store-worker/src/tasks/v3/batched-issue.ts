import { DocumentStore } from "@govtechsg/document-store/src/contracts/DocumentStore";
import { Wallet } from "ethers";
import { logger } from 'src/logger';
import { OpenAttestationVersion as Version } from 'src/constants';
import {
  InvalidDocuments,
  BatchDocuments,
  IssuedDocuments,
  UnprocessedDocuments,
  UnprocessedDocumentsQueue
} from "src/repos";
import { RestoreBatch } from "src/tasks/common/restore-batch";
import { Batch } from 'src/tasks/common/data';
import { Task } from "src/tasks/common/interfaces";
import { SaveBatch } from "src/tasks/common/save-batch";
import { ComposeIssueBatch } from "src/tasks/common/compose-issue-batch";
import { WrapBatch } from "src/tasks/common/wrap-batch";
import { IssueBatch } from "src/tasks/v3/issue-batch";

export interface IBatchedIssueProps{
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
  restoreAttempts: number,
  restoreAttemptsIntervalSeconds: number,
  composeAttempts: number,
  composeAttemptsIntervalSeconds: number,
  issueAttempts: number
  issueAttemptsIntervalSeconds: number,
  saveAttempts: number,
  saveAttemptsIntervalSeconds: number
}


export class BatchedIssue implements Task<void>{
  private props: IBatchedIssueProps;

  constructor(props: IBatchedIssueProps){
    this.props = props;
  }

  /* istanbul ignore next */
  async start(){
    logger.info(`BatchedIssue[${Version.V3}] task started`);
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
    const version = Version.V3;
    await new RestoreBatch({
      version,
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
      version,
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

    await new WrapBatch({version, batch}).start()

    await new IssueBatch({
      signer: this.props.wallet,
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
