/* istanbul ignore file */
import { logger } from 'src/logger';
import { getBatchedSignerEnvConfig } from 'src/config';
import {
  UnprocessedDocuments,
  UnprocessedDocumentsQueue,
  BatchDocuments,
  IssuedDocuments,
  InvalidDocuments
} from 'src/repos';
import {
  connectWallet,
  connectDocumentStore,
} from 'src/document-store';
import { BatchedIssue } from 'src/tasks/v3/batched-issue';

async function main(){
  const config = getBatchedSignerEnvConfig();
  const wallet = await connectWallet(config);
  logger.info('Config loaded');
  logger.info('%O', config);
  await new BatchedIssue({
    invalidDocuments: new InvalidDocuments(config),
    unprocessedDocuments: new UnprocessedDocuments(config),
    batchDocuments: new BatchDocuments(config),
    issuedDocuments: new IssuedDocuments(config),
    unprocessedDocumentsQueue: new UnprocessedDocumentsQueue(config),
    wallet: wallet,
    documentStore: await connectDocumentStore(config, wallet),
    messageWaitTime: config.MESSAGE_WAIT_TIME,
    messageVisibilityTimeout: config.MESSAGE_VISIBILITY_TIMEOUT,
    batchSizeBytes: config.BATCH_SIZE_BYTES,
    batchTimeSeconds: config.BATCH_TIME_SECONDS,
    restoreAttempts: config.RESTORE_ATTEMPTS,
    restoreAttemptsIntervalSeconds: config.RESTORE_ATTEMPTS_INTERVAL_SECONDS,
    composeAttempts: config.COMPOSE_ATTEMPTS,
    composeAttemptsIntervalSeconds: config.COMPOSE_ATTEMPTS_INTERVAL_SECONDS,
    issueAttempts: config.ISSUE_ATTEMPTS,
    issueAttemptsIntervalSeconds: config.ISSUE_ATTEMPTS_INTERVAL_SECONDS,
    saveAttempts: config.SAVE_ATTEMPTS,
    saveAttemptsIntervalSeconds: config.SAVE_ATTEMPTS_INTERVAL_SECONDS
  }).start();
}

main().catch(logger.error);
