import { wrapDocuments, wrapDocument } from '@govtechsg/open-attestation';
import { getBatchedDocumentStoreTaskEnvConfig } from 'src/config';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import { logger } from 'src/logger';
import { generateDocumentsMap } from 'tests/utils';

describe('Testing batching method costs', ()=>{
  jest.setTimeout(1000 * 100);
  const config = getBatchedDocumentStoreTaskEnvConfig();
  test('Test', async ()=>{
    const BATCH_SIZE = 100;
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);
    const collectionBatching = async()=>{
      const documents = generateDocumentsMap(BATCH_SIZE);
      const wrappedDocuments = wrapDocuments(Array.from<any>(documents.values()));
      const merkleRoot = wrappedDocuments[0].signature.merkleRoot;
      expect(wrappedDocuments.every(e=>e.signature.merkleRoot === merkleRoot)).toBeTruthy();
      const transaction = await documentStore.populateTransaction.issue(`0x${merkleRoot}`);
      const gasLimit = (await wallet.estimateGas(transaction)).toNumber();
      return gasLimit;
    }
    const bulkIssueBatching = async()=>{
      const documents = generateDocumentsMap(BATCH_SIZE);
      const merkleRoots = Array.from<any>(documents.values()).map(document=>'0x' + wrapDocument(document).signature.merkleRoot);
      const transaction = await documentStore.populateTransaction.bulkIssue(merkleRoots);
      const gasLimit = (await wallet.estimateGas(transaction)).toNumber();
      return gasLimit;
    }
    const bulkIssueBatchingGasLimit = await bulkIssueBatching();
    const collectionBatchingGasLimit = await collectionBatching();
    logger.info('BATCH_SIZE=%s', BATCH_SIZE);
    logger.info('bulkIssueBatchingGasLimit=%s', bulkIssueBatchingGasLimit);
    logger.info('bulkIssueGasPerDocument=%s', bulkIssueBatchingGasLimit/BATCH_SIZE);
    logger.info('bulkIssueGasPerDocument/issueGasPerDocument=%s', bulkIssueBatchingGasLimit/BATCH_SIZE/collectionBatchingGasLimit);
    logger.info('collectionBatchingGasLimit=%s', collectionBatchingGasLimit);
    logger.info('bulkIssueBatchingGasLimit/collectionBatchingGasLimit=%s', bulkIssueBatchingGasLimit/collectionBatchingGasLimit);
  });
});
