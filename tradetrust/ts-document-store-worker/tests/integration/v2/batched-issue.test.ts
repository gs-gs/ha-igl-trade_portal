import { getData } from '@govtechsg/open-attestation';
import {
  InvalidDocuments,
  UnprocessedDocuments,
  BatchDocuments,
  IssuedDocuments,
  UnprocessedDocumentsQueue
} from 'src/repos';
import { getBatchedIssueEnvConfig } from 'src/config';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import { BatchedIssue } from 'src/tasks/v2/batched-issue';
import { clearQueue, clearBucket, generateDocumentsMapV2 } from 'tests/utils';

describe('BatchedIssue Task V2', ()=>{

  jest.setTimeout(1000 * 100);


  const config = getBatchedIssueEnvConfig();

  const unprocessedDocuments = new UnprocessedDocuments(config);
  const batchDocuments = new BatchDocuments(config);
  const issuedDocuments = new IssuedDocuments(config);
  const unprocessedDocumentsQueue = new UnprocessedDocumentsQueue(config);
  const invalidDocuments = new InvalidDocuments(config);

  beforeEach(async ()=>{
    await clearQueue(config.UNPROCESSED_QUEUE_URL);
    await clearBucket(config.UNPROCESSED_BUCKET_NAME);
    await clearBucket(config.BATCH_BUCKET_NAME);
    await clearBucket(config.ISSUED_BUCKET_NAME);
  }, 1000 * 60);

  test('test complete by size', async ()=>{

    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);

    const documentsCount = 20;
    const documents = generateDocumentsMapV2(documentsCount);
    const expectedBatchDocuments = Array.from<[string, any]>(documents.entries()).slice(0, 10);
    for(let [key, document] of documents){
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)})
    }
    let maxBatchSizeBytes: number = 0;
    for(let [key] of expectedBatchDocuments){
      let documentS3Object = await unprocessedDocuments.get({Key: key})
      maxBatchSizeBytes += documentS3Object.ContentLength!;
    }

    const processDocuments = new BatchedIssue({
      invalidDocuments,
      unprocessedDocuments,
      batchDocuments,
      issuedDocuments,
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
      issueAttempts: 1,
      issueAttemptsIntervalSeconds: 1,
      saveAttempts: 1,
      saveAttemptsIntervalSeconds: 1
    });

    await processDocuments.next();

    const signatures = Array<string>();
    const batchDocumentsList = (await batchDocuments.list()).Contents??[];
    const unprocessedDocumentsList = (await unprocessedDocuments.list()).Contents??[];

    expect(batchDocumentsList.length).toBe(0);
    expect(unprocessedDocumentsList.length).toBe(documentsCount - expectedBatchDocuments.length);

    for(let [key, document] of expectedBatchDocuments){
      const issuedDocumentS3Object = await issuedDocuments.get({Key: key});
      const issuedDocument = JSON.parse(issuedDocumentS3Object.Body!.toString());
      signatures.push(issuedDocument.signature.merkleRoot);
      const unwrappedIssuedDocument = getData(issuedDocument);
      expect(unwrappedIssuedDocument).toEqual(document);
    }
    expect(signatures.every(signature=> signature == signatures[0])).toBe(true);
  });

  test('test complete by time', async ()=>{

    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);

    const documentsCount = 20;
    const documents = generateDocumentsMapV2(documentsCount);
    const expectedBatchDocuments = Array.from<[string, any]>(documents.entries());
    for(let [key, document] of documents){
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)})
    }
    let maxBatchSizeBytes: number = 0;
    for(let [key] of expectedBatchDocuments){
      let documentS3Object = await unprocessedDocuments.get({Key: key})
      maxBatchSizeBytes += documentS3Object.ContentLength!;
    }

    const processDocuments = new BatchedIssue({
      invalidDocuments,
      unprocessedDocuments,
      batchDocuments,
      issuedDocuments,
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
      issueAttempts: 1,
      issueAttemptsIntervalSeconds: 1,
      saveAttempts: 1,
      saveAttemptsIntervalSeconds: 1
    });

    await processDocuments.next();

    const signatures = Array<string>();
    const batchDocumentsList = (await batchDocuments.list()).Contents??[];
    const unprocessedDocumentsList = (await unprocessedDocuments.list()).Contents??[];

    expect(batchDocumentsList.length).toBe(0);
    expect(unprocessedDocumentsList.length).toBe(documentsCount - expectedBatchDocuments.length);

    for(let [key, document] of expectedBatchDocuments){
      const issuedDocumentS3Object = await issuedDocuments.get({Key: key});
      const issuedDocument = JSON.parse(issuedDocumentS3Object.Body!.toString());
      signatures.push(issuedDocument.signature.merkleRoot);
      const unwrappedIssuedDocument = getData(issuedDocument);
      expect(unwrappedIssuedDocument).toEqual(document);
    }
    expect(signatures.every(signature=> signature == signatures[0])).toBe(true);
  });

})
