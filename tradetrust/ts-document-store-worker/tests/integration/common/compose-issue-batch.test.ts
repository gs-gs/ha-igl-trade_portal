import {
  SchemaId,
  wrapDocument as wrapDocumentV2,
  __unsafe__use__it__at__your__own__risks__wrapDocument as wrapDocumentV3
} from '@govtechsg/open-attestation';
import { OpenAttestationVersion as Version } from 'src/constants';
import { getBatchedIssueEnvConfig } from 'src/config';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import { Batch } from 'src/tasks/common/data';
import { ComposeIssueBatch } from 'src/tasks/common/compose-issue-batch';
import {
  InvalidDocuments,
  UnprocessedDocuments,
  BatchDocuments,
  UnprocessedDocumentsQueue
} from 'src/repos';
import {
  clearQueue,
  clearBucket,
  documentV2,
  documentV3,
  generateDocumentsMapV2,
  generateDocumentsMapV3,
  createInvalidDocumentReasonAssert
} from 'tests/utils';


describe('ComposeIssueBatch Task', ()=>{
  const config = getBatchedIssueEnvConfig();
  beforeEach(async ()=>{
    await clearQueue(config.UNPROCESSED_QUEUE_URL);
    await clearBucket(config.UNPROCESSED_BUCKET_NAME);
    await clearBucket(config.BATCH_BUCKET_NAME);
    jest.setTimeout(1000 * 60);
  });

  const invalidDocuments = new InvalidDocuments(config);
  const unprocessedDocuments = new UnprocessedDocuments(config);
  const batchDocuments = new BatchDocuments(config);
  const unprocessedDocumentsQueue = new UnprocessedDocumentsQueue(config);

  const BATCH_BACKUP_TEST_PARAMS = [
    {
      version: Version.V2,
      generateDocumentsMap: generateDocumentsMapV2
    },
    {
      version: Version.V3,
      generateDocumentsMap: generateDocumentsMapV3
    }
  ];

  describe.each(BATCH_BACKUP_TEST_PARAMS)('Batch Backup', ({version, generateDocumentsMap})=>{
    test(version, async ()=>{
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);
      const documents = generateDocumentsMap(10);
      for(let [key, document] of documents){
        await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
      }
      const batch = new Batch();
      const composeBatch = new ComposeIssueBatch({
        version,
        invalidDocuments,
        unprocessedDocuments,
        batchDocuments,
        unprocessedDocumentsQueue,
        batchTimeSeconds: 5,
        batchSizeBytes: 1024 * 1024 * 1024,
        messageWaitTime: 1,
        messageVisibilityTimeout: 60,
        wallet: wallet,
        documentStore: documentStore,
        attempts: 1,
        attemptsIntervalSeconds: 1,
        batch
      });
      await composeBatch.start();
      for(let [key, document] of documents){
        expect(document).toEqual(batch.unwrappedDocuments.get(key)?.body);
        const s3Object = await batchDocuments.get({Key: key});
        expect(document).toEqual(JSON.parse(s3Object.Body?.toString() || ''))
      }
    });
  });
  const INVALID_DOCUMENTS_HANDLING_TEST_PARAMS = [
    {
      version: Version.V2,
      documentVersion: SchemaId.v2,
      document: documentV2,
      wrap: async (document:any)=>wrapDocumentV2(document),
      invalidDocumentStoreAddress: '0x0000000000000000000000000000000000000000',
      invalidDocumentStoreOverride: {
        issuers:[
          {
            name: 'DEMO STORE',
            documentStore: '0x0000000000000000000000000000000000000000',
            identityProof: {
              type: 'DNS-TXT',
              location: 'tradetrust.io'
            }
          }
        ]
      }
    },
    {
      version: Version.V3,
      documentVersion: SchemaId.v3,
      document: documentV3,
      wrap: async (document:any)=>await wrapDocumentV3(document),
      invalidDocumentStoreAddress: '0x0000000000000000000000000000000000000000',
      invalidDocumentStoreOverride: {
        openAttestationMetadata: {
          proof: {
            value: 'did:ethr:0x0000000000000000000000000000000000000000'
          }
        }
      }
    }
  ];
  describe.each(INVALID_DOCUMENTS_HANDLING_TEST_PARAMS)('Invalid documents handling', ({
    version,
    document,
    wrap,
    documentVersion,
    invalidDocumentStoreAddress,
    invalidDocumentStoreOverride
  })=>{
    test(version, async ()=>{
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);
      const documents = new Map<string, any>();
      documents.set('non-json-document', 'non-json-document-body');
      documents.set('deleted-document', document());
      documents.set('invalid-document', {version: documentVersion});
      documents.set('invalid-document-version', {version: 'invalid'});
      documents.set('invalid-document-store-document', document(invalidDocumentStoreOverride));
      documents.set('wrapped-document', await wrap(document()));
      documents.set('regular-document', document());
      // adding the document and modifying its event to set invalid etag
      await unprocessedDocuments.put({Key: 'invalid-etag-document', Body: JSON.stringify(document())});
      const invalidETagDocumentPutEvent: any = await unprocessedDocumentsQueue.get();
      invalidETagDocumentPutEvent.Body = JSON.parse(invalidETagDocumentPutEvent.Body);
      invalidETagDocumentPutEvent.Body.Records[0].s3.object.eTag = 'invalid-etag';
      await unprocessedDocumentsQueue.delete({ReceiptHandle: invalidETagDocumentPutEvent.ReceiptHandle});
      await unprocessedDocumentsQueue.post({MessageBody: JSON.stringify(invalidETagDocumentPutEvent.Body)});

      for(let [key, document] of documents){
        if(typeof document !== 'string'){
          document = JSON.stringify(document);
        }
        await unprocessedDocuments.put({Key: key, Body: document});
      }
      await unprocessedDocuments.delete({Key: 'deleted-document'});

      const batch = new Batch();
      const composeBatch = new ComposeIssueBatch({
        version,
        invalidDocuments,
        unprocessedDocuments,
        batchDocuments,
        unprocessedDocumentsQueue,
        batchTimeSeconds: 5,
        batchSizeBytes: 1024 * 1024 * 1024,
        messageWaitTime: 1,
        messageVisibilityTimeout: 60,
        wallet: wallet,
        documentStore: documentStore,
        batch
      });
      await composeBatch.start();

      const invalidDocumentReasonAssert = createInvalidDocumentReasonAssert(batch, documents, invalidDocuments);
      expect(batch.wrappedDocuments.size).toBe(0);
      expect(batch.unwrappedDocuments.size).toBe(1);
      await invalidDocumentReasonAssert(
        'invalid-document-store-document',
        `Invalid document store address. Expected: ${documentStore.address}. Got: ${invalidDocumentStoreAddress}`
      )
      await invalidDocumentReasonAssert(
        'non-json-document',
        'Document body is not a valid JSON'
      )
      await invalidDocumentReasonAssert(
        'invalid-document',
        'Invalid document schema'
      )
      await invalidDocumentReasonAssert(
        'invalid-document-version',
        'Invalid document version'
      )
      await invalidDocumentReasonAssert(
        'wrapped-document',
        'Document is wrapped'
      )
      expect(batch.unwrappedDocuments.get('non-json-document')).toBeFalsy();
      expect(batch.unwrappedDocuments.get('deleted-document')).toBeFalsy();
      expect(batch.unwrappedDocuments.get('invalid-document')).toBeFalsy();
      expect(batch.unwrappedDocuments.get('invalid-document-version')).toBeFalsy();
      expect(batch.unwrappedDocuments.get('invalid-document-store-document')).toBeFalsy();
      expect(batch.unwrappedDocuments.get('invalid-etag-document')).toBeFalsy();
      expect(batch.unwrappedDocuments.get('wrapped-document')).toBeFalsy();
      expect(batch.unwrappedDocuments.get('regular-document')).toBeTruthy();
    });
  });

  const COMPLETE_BY_TIME_TEST_PARAMS = [
    {
      version: Version.V2,
      generateDocumentsMap: generateDocumentsMapV2
    },
    {
      version: Version.V3,
      generateDocumentsMap: generateDocumentsMapV3
    }
  ];

  describe.each(COMPLETE_BY_TIME_TEST_PARAMS)('Complete by time', ({version, generateDocumentsMap})=>{
    test(version, async ()=>{
      jest.setTimeout(1000 * 10);
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);

      const documents = generateDocumentsMap(10);
      for(let [key, document] of documents){
        await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
      }
      const batch = new Batch();
      const composeBatch = new ComposeIssueBatch({
        version,
        invalidDocuments,
        unprocessedDocuments,
        batchDocuments,
        unprocessedDocumentsQueue,
        batchTimeSeconds: 5,
        batchSizeBytes: 1024 * 1024 * 1024,
        messageWaitTime: 1,
        messageVisibilityTimeout: 60,
        wallet: wallet,
        documentStore: documentStore,
        batch
      });

      await composeBatch.start();

      const expectedBatchDocuments = Array.from<any>(documents.values());
      const resultingBatchDocuments = Array.from<any>(batch.unwrappedDocuments.values()).map(entry=>entry.body);

      expect(resultingBatchDocuments).toEqual(expectedBatchDocuments);
    });
  });

  const COMPLETE_BY_SIZE_TEST_PARAMS = [
    {
      version: Version.V2,
      generateDocumentsMap: generateDocumentsMapV2
    },
    {
      version: Version.V3,
      generateDocumentsMap: generateDocumentsMapV3
    }
  ];
  describe.each(COMPLETE_BY_SIZE_TEST_PARAMS)('Complete by size', ({version, generateDocumentsMap})=>{
    test(version, async ()=>{
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);

      const documentsCount = 20;
      const expectedBatchDocumentsCount = 10;
      let maxBatchSizeBytes = 0;
      const documents = generateDocumentsMap(documentsCount)

      let documentIndex = 0;
      for(let [key, document] of documents){
        await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
        if(documentIndex < expectedBatchDocumentsCount){
          maxBatchSizeBytes += (await unprocessedDocuments.get({Key:key})).ContentLength??0;
        }
        documentIndex++;
      }
      const batch = new Batch();
      const composeBatch = new ComposeIssueBatch({
        version,
        invalidDocuments,
        unprocessedDocuments,
        batchDocuments,
        unprocessedDocumentsQueue,
        batchTimeSeconds: 10,
        batchSizeBytes: maxBatchSizeBytes,
        messageWaitTime: 1,
        messageVisibilityTimeout: 60,
        wallet: wallet,
        documentStore: documentStore,
        batch
      });
      await composeBatch.start();

      const expectedBatchDocuments = Array.from<any>(documents.values()).slice(0, expectedBatchDocumentsCount);
      const resultingBatchDocuments = Array.from<any>(batch.unwrappedDocuments.values()).map(entry=>entry.body);
      expect(resultingBatchDocuments).toEqual(expectedBatchDocuments);
    });
  });
});
