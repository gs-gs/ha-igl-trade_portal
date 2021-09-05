import {
  wrapDocument as wrapDocumentV2,
  __unsafe__use__it__at__your__own__risks__wrapDocument as wrapDocumentV3
} from '@govtechsg/open-attestation';
import { OpenAttestationVersion as Version } from 'src/constants';
import {
  InvalidDocuments,
  UnprocessedDocuments,
  BatchDocuments,
  RevokedDocuments,
  UnprocessedDocumentsQueue
} from 'src/repos';
import { getBatchedRevokeEnvConfig } from 'src/config';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import  { BatchedRevoke } from 'src/tasks/common/batched-revoke';
import {
  clearQueue,
  clearBucket,
  generateDocumentsMapV2,
  generateDocumentsMapV3
} from 'tests/utils';

const TEST_PARAMS = [
  {
    version: Version.V2,
    wrapDocument: async (document: any)=>wrapDocumentV2(document),
    generateDocumentsMap: generateDocumentsMapV2,
    getSignature: (document: any)=>document.signature.targetHash
  },
  {
    version: Version.V3,
    wrapDocument: async (document: any)=>await wrapDocumentV3(document),
    generateDocumentsMap: generateDocumentsMapV3,
    getSignature: (document: any)=>document.proof.targetHash
  }
]

describe.each(TEST_PARAMS)('Batched Revoke task', ({
  version,
  wrapDocument,
  generateDocumentsMap,
  getSignature
})=>{

  const config = getBatchedRevokeEnvConfig();
  const documentsCount = 5;
  const unwrappedDocuments = generateDocumentsMap(documentsCount);

  const generateWrappedDocuments = async (unwrappedDocuments: Map<string, any>)=>{
    const wrappedDocuments = new Map<string,any>();
    for(let [key, document] of unwrappedDocuments){
      wrappedDocuments.set(key, await wrapDocument(document));
    }
    return wrappedDocuments;
  }

  const invalidDocuments = new InvalidDocuments(config);
  const unprocessedDocuments = new UnprocessedDocuments(config);
  const batchDocuments = new BatchDocuments(config);
  const revokedDocuments = new RevokedDocuments(config);
  const unprocessedDocumentsQueue = new UnprocessedDocumentsQueue(config);

  beforeEach(async ()=>{
    await clearQueue(config.UNPROCESSED_QUEUE_URL);
    await clearBucket(config.UNPROCESSED_BUCKET_NAME);
    await clearBucket(config.BATCH_BUCKET_NAME);
    await clearBucket(config.REVOKED_BUCKET_NAME);
    jest.setTimeout(1000 * 100);
  }, 1000 * 60);

  describe(version, ()=>{
    test('Complete by size', async ()=>{
      const wrappedDocuments = await generateWrappedDocuments(unwrappedDocuments);
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);

      let maxBatchSizeBytes = 0;
      for(let [key, document] of wrappedDocuments){
        await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
        let documentS3Object = await unprocessedDocuments.get({Key: key})
        maxBatchSizeBytes += documentS3Object.ContentLength!;
      }

      const processDocuments = new BatchedRevoke({
        version,
        invalidDocuments,
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
        expect(await documentStore.isRevoked(`0x${getSignature(document)}`)).toBe(true);
      }
    });

    test('Complete by time', async ()=>{
      const wrappedDocuments = await generateWrappedDocuments(unwrappedDocuments);
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);

      let maxBatchSizeBytes = 0;
      for(let [key, document] of wrappedDocuments){
        await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
        let documentS3Object = await unprocessedDocuments.get({Key: key})
        maxBatchSizeBytes += documentS3Object.ContentLength!;
      }

      const processDocuments = new BatchedRevoke({
        version,
        invalidDocuments,
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
        expect(await documentStore.isRevoked(`0x${getSignature(document)}`)).toBe(true);
      }
    });
  });
})
