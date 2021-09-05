import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import { Wallet } from 'ethers';
import { OpenAttestationVersion as Version } from 'src/constants';
import { logger } from 'src/logger';
import {
  InvalidDocuments,
  BatchDocuments,
  RevokedDocuments,
  UnprocessedDocuments,
  UnprocessedDocumentsQueue
} from 'src/repos';

import { Batch } from 'src/tasks/common/data';
import { Task } from 'src/tasks/common/interfaces';
import { RestoreBatch } from 'src/tasks/common/restore-batch';
import { ComposeRevokeBatch } from 'src/tasks/common/compose-revoke-batch';
import { RevokeBatch } from 'src/tasks/common/revoke-batch';
import { SaveBatch } from 'src/tasks/common/save-batch';


export interface IBatchedRevokeProps{
  version: Version,
  invalidDocuments: InvalidDocuments,
  unprocessedDocuments: UnprocessedDocuments,
  batchDocuments: BatchDocuments,
  revokedDocuments: RevokedDocuments,
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
  revokeAttempts: number
  revokeAttemptsIntervalSeconds: number,
  saveAttempts: number,
  saveAttemptsIntervalSeconds: number
}



export class BatchedRevoke implements Task<Promise<void>>{

  private props: IBatchedRevokeProps;

  constructor(props: IBatchedRevokeProps){
    this.props = Object.assign({}, props);
  }

  async next(){
    const batch = new Batch();
    const {version} = this.props;
    await new RestoreBatch({
      batch,
      version,
      wrapped: true,
      documentStore: this.props.documentStore,
      invalidDocuments: this.props.invalidDocuments,
      batchDocuments: this.props.batchDocuments,
      batchSizeBytes: this.props.batchSizeBytes,
      batchTimeSeconds: this.props.batchTimeSeconds,
      attempts: this.props.restoreAttempts,
      attemptsIntervalSeconds: this.props.restoreAttemptsIntervalSeconds
    }).start();

    await new ComposeRevokeBatch({
      batch,
      version,
      invalidDocuments: this.props.invalidDocuments,
      batchDocuments: this.props.batchDocuments,
      unprocessedDocuments: this.props.unprocessedDocuments,
      unprocessedDocumentsQueue: this.props.unprocessedDocumentsQueue,
      messageWaitTime: this.props.messageWaitTime,
      messageVisibilityTimeout: this.props.messageVisibilityTimeout,
      attempts: this.props.revokeAttempts,
      attemptsIntervalSeconds: this.props.revokeAttemptsIntervalSeconds,
      batchSizeBytes: this.props.batchSizeBytes,
      batchTimeSeconds: this.props.batchTimeSeconds,
      wallet: this.props.wallet,
      documentStore: this.props.documentStore
    }).start()

    if(batch.isEmpty()){
      logger.info('The batch is empty, skipping further steps');
      return;
    }

    await new RevokeBatch({
      batch,
      version,
      wallet: this.props.wallet,
      documentStore: this.props.documentStore,
      attempts: this.props.revokeAttempts,
      attemptsIntervalSeconds: this.props.revokeAttemptsIntervalSeconds,
      gasPriceLimitGwei: this.props.gasPriceLimitGwei,
      gasPriceMultiplier: this.props.gasPriceMultiplier,
      transactionTimeoutSeconds: this.props.transactionTimeoutSeconds,
      transactionConfirmationThreshold: this.props.transactionConfirmationThreshold
    }).start()

    await new SaveBatch({
      batch,
      batchDocuments: this.props.batchDocuments,
      processedDocuments: this.props.revokedDocuments,
      attempts: this.props.saveAttempts,
      attemptsIntervalSeconds: this.props.saveAttemptsIntervalSeconds
    }).start();
  }

  async start(){
    logger.info('BatchedRevoke[%s] task started', this.props.version);
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
}
