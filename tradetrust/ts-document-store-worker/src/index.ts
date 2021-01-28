import { logger } from 'src/logger';
import config from 'src/config';
import {
  UnprocessedDocuments,
  UnprocessedDocumentsQueue,
  BatchDocuments,
  IssuedDocuments
} from 'src/repos';
import {
  connectWallet,
  connectDocumentStore,
} from 'src/document-store';
import { ProcessDocuments } from 'src/tasks';

async function main(){
  const wallet = await connectWallet();
  await new ProcessDocuments(
    new UnprocessedDocuments(),
    new BatchDocuments(),
    new IssuedDocuments(),
    new UnprocessedDocumentsQueue(),
    wallet,
    await connectDocumentStore(wallet),
    config.MESSAGE_WAIT_TIME,
    config.MESSAGE_VISIBILITY_TIMEOUT,
    config.MAX_BATCH_SIZE_BYTES,
    config.MAX_BATCH_TIME_SECONDS,
    config.TRANSACTION_TIMEOUT_SECONDS,
    config.TRANSACTION_CONFIRMATION_THRESHOLD,
    config.GAS_PRICE_MULTIPLIER
  ).start();
}

main().catch(logger.error);
