import { logger } from './logger';
import config from './config';
import {
  UnprocessedDocuments,
  UnprocessedDocumentsQueue,
  BatchDocuments,
  IssuedDocuments
} from './repos';
import {
  connectWallet,
  connectDocumentStore,
} from './document-store';
import { ProcessDocuments } from './tasks';

async function main(){
  const wallet = await connectWallet();
  await new ProcessDocuments({
    unprocessedDocuments: new UnprocessedDocuments(),
    batchDocuments: new BatchDocuments(),
    issuedDocuments: new IssuedDocuments(),
    unprocessedDocumentsQueue: new UnprocessedDocumentsQueue(),
    wallet: wallet,
    documentStore: await connectDocumentStore(wallet),
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
    issueAttempts: config.ISSUE_ATTEMPTS,
    issueAttemptsIntervalSeconds: config.ISSUE_ATTEMPTS_INTERVAL_SECONDS,
    saveAttempts: config.SAVE_ATTEMPTS,
    saveAttemptsIntervalSeconds: config.SAVE_ATTEMPTS_INTERVAL_SECONDS
  }).start();
}

main().catch(logger.error);
