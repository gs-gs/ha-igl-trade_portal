import { wrapDocument } from '@govtechsg/open-attestation';
import {
  UnprocessedDocuments,
  BatchDocuments,
  RevokedDocuments,
  UnprocessedDocumentsQueue
} from 'src/repos';
import { getBatchedRevokeEnvConfig } from 'src/config';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import { BatchedRevoke } from 'src/tasks';
import { clearQueue, clearBucket, generateDocumentsMap } from 'tests/utils';

describe('Test', ()=>{

  jest.setTimeout(1000 * 100);


  const config = getBatchedRevokeEnvConfig();
  const documentsCount = 5;
  const unwrappeDocuments = generateDocumentsMap(documentsCount);

  const generateWrappedDocuments = (unwrappedDocuments: Map<string, any>)=>{
    const wrappedDocuments = new Map<string,any>();
    for( let [key, document] of unwrappeDocuments){
      wrappedDocuments.set(key, wrapDocument(document));
    }
    return wrappedDocuments;
  }

  const unprocessedDocuments = new UnprocessedDocuments(config);
  const batchDocuments = new BatchDocuments(config);
  const revokedDocuments = new RevokedDocuments(config);
  const unprocessedDocumentsQueue = new UnprocessedDocumentsQueue(config);

  beforeEach(async (done)=>{
    await clearQueue(config.UNPROCESSED_QUEUE_URL);
    await clearBucket(config.UNPROCESSED_BUCKET_NAME);
    await clearBucket(config.BATCH_BUCKET_NAME);
    await clearBucket(config.REVOKED_BUCKET_NAME);
    done();
  }, 1000 * 60);

  test('test complete by size', async ()=>{
    const wrappedDocuments = generateWrappedDocuments(unwrappeDocuments);
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);

    let maxBatchSizeBytes = 0;
    for(let [key, document] of wrappedDocuments){
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
      let documentS3Object = await unprocessedDocuments.get({Key: key})
      maxBatchSizeBytes += documentS3Object.ContentLength!;
    }

    const processDocuments = new BatchedRevoke({
      unprocessedDocuments,
      batchDocuments,
      revokedDocuments,
      unprocessedDocumentsQueue,
      wallet,
      documentStore,
      gasPriceLimitGwei: 200,
      gasPriceMultiplier: 1.2,
      batchSizeBytes: maxBatchSizeBytes,
      batchTimeSeconds: 10,
      messageWaitTime: 1,
      messageVisibilityTimeout: 60,
      transactionTimeoutSeconds: 180,
      transactionConfirmationThreshold: 1,
      restoreAttempts: 1,
      restoreAttemptsIntervalSeconds: 1,
      composeAttempts: 1,
      composeAttemptsIntervalSeconds: 1,
      revokeAttempts: 1,
      revokeAttemptsIntervalSeconds: 1,
      saveAttempts: 1,
      saveAttemptsIntervalSeconds: 1
    });

    await processDocuments.next();
    const batchDocumentsList = (await batchDocuments.list()).Contents??[];
    const unprocessedDocumentsList = (await unprocessedDocuments.list()).Contents??[];
    expect(batchDocumentsList.length).toBe(0);
    expect(unprocessedDocumentsList.length).toBe(0);
    for( let [key, document] of wrappedDocuments){
      const s3Document = JSON.parse((await revokedDocuments.get({Key: key}))!.Body!.toString());
      expect(document).toEqual(s3Document);
      expect(await documentStore.isRevoked(`0x${document.signature.targetHash}`)).toBe(true);
    }
  });

  test('test complete by size', async ()=>{
    const wrappedDocuments = generateWrappedDocuments(unwrappeDocuments);
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);

    let maxBatchSizeBytes = 0;
    for(let [key, document] of wrappedDocuments){
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
      let documentS3Object = await unprocessedDocuments.get({Key: key})
      maxBatchSizeBytes += documentS3Object.ContentLength!;
    }

    const processDocuments = new BatchedRevoke({
      unprocessedDocuments,
      batchDocuments,
      revokedDocuments,
      unprocessedDocumentsQueue,
      wallet,
      documentStore,
      gasPriceLimitGwei: 200,
      gasPriceMultiplier: 1.2,
      batchSizeBytes: maxBatchSizeBytes * 2,
      batchTimeSeconds: 10,
      messageWaitTime: 1,
      messageVisibilityTimeout: 60,
      transactionTimeoutSeconds: 180,
      transactionConfirmationThreshold: 1,
      restoreAttempts: 1,
      restoreAttemptsIntervalSeconds: 1,
      composeAttempts: 1,
      composeAttemptsIntervalSeconds: 1,
      revokeAttempts: 1,
      revokeAttemptsIntervalSeconds: 1,
      saveAttempts: 1,
      saveAttemptsIntervalSeconds: 1
    });

    await processDocuments.next();
    const batchDocumentsList = (await batchDocuments.list()).Contents??[];
    const unprocessedDocumentsList = (await unprocessedDocuments.list()).Contents??[];
    expect(batchDocumentsList.length).toBe(0);
    expect(unprocessedDocumentsList.length).toBe(0);
    for( let [key, document] of wrappedDocuments){
      const s3Document = JSON.parse((await revokedDocuments.get({Key: key}))!.Body!.toString());
      expect(document).toEqual(s3Document);
      expect(await documentStore.isRevoked(`0x${document.signature.targetHash}`)).toBe(true);
    }
  });

})
