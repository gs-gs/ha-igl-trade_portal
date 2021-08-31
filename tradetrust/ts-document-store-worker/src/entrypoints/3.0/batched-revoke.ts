/* istanbul ignore file */
import { logger } from 'src/logger';
import { OpenAttestationVersion as Version } from 'src/constants';
import { getBatchedRevokeEnvConfig } from 'src/config';
import {
  UnprocessedDocuments,
  UnprocessedDocumentsQueue,
  BatchDocuments,
  RevokedDocuments,
  InvalidDocuments
} from 'src/repos';
import {
  connectWallet,
  connectDocumentStore,
} from 'src/document-store';
import { BatchedRevoke } from 'src/tasks/common/batched-revoke';

async function main(){
  const config = getBatchedRevokeEnvConfig();
  const wallet = await connectWallet(config);
  logger.info('Config loaded');
  logger.info('%O', config);
  await new BatchedRevoke({
    version: Version.V3,
    invalidDocuments: new InvalidDocuments(config),
    unprocessedDocuments: new UnprocessedDocuments(config),
    batchDocuments: new BatchDocuments(config),
    revokedDocuments: new RevokedDocuments(config),
    unprocessedDocumentsQueue: new UnprocessedDocumentsQueue(config),
    wallet: wallet,
    documentStore: await connectDocumentStore(config, wallet),
    messageWaitTime: config.MESSAGE_WAIT_TIME,
    messageVisibilityTimeout: config.MESSAGE_VISIBILITY_TIMEOUT,
    batchSizeBytes: config.BATCH_SIZE_BYTES,
    batchTimeSeconds: config.BATCH_TIME_SECONDS,
    transactionTimeoutSeconds: config.TRANSACTION_TIMEOUT_SECONDS,
    transactionConfirmationThreshold: config.TRANSACTION_CONFIRMATION_THRESHOLD,
    gasPriceMultiplier: config.GAS_PRICE_MULTIPLIER,
    gasPriceLimitGwei: config.GAS_PRICE_LIMIT_GWEI,
    restoreAttempts: config.RESTORE_ATTEMPTS,
    restoreAttemptsIntervalSeconds: config.RESTORE_ATTEMPTS_INTERVAL_SECONDS,
    composeAttempts: config.COMPOSE_ATTEMPTS,
    composeAttemptsIntervalSeconds: config.COMPOSE_ATTEMPTS_INTERVAL_SECONDS,
    revokeAttempts: config.REVOKE_ATTEMPTS,
    revokeAttemptsIntervalSeconds: config.REVOKE_ATTEMPTS_INTERVAL_SECONDS,
    saveAttempts: config.SAVE_ATTEMPTS,
    saveAttemptsIntervalSeconds: config.SAVE_ATTEMPTS_INTERVAL_SECONDS
  }).start();
}

main().catch(logger.error);
