import {
  wrapDocument as wrapDocumentV2,
  __unsafe__use__it__at__your__own__risks__wrapDocument as wrapDocumentV3
} from '@govtechsg/open-attestation';
import { getBatchedIssueEnvConfig } from 'src/config';
import { OpenAttestationVersion as Version } from 'src/constants';
import { Batch } from 'src/tasks/common/data';
import { RestoreBatch } from 'src/tasks/common/restore-batch';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import {
  BatchDocuments,
  InvalidDocuments
} from 'src/repos';
import {
  clearBucket,
  generateDocumentsMapV2,
  generateDocumentsMapV3
} from 'tests/utils';


const TEST_PARAMS = [
  {
    version: Version.V2,
    wrapDocument: async (document: any)=>wrapDocumentV2(document),
    generateDocumentsMap: generateDocumentsMapV2
  },
  {
    version: Version.V3,
    wrapDocument: async (document: any)=>await wrapDocumentV3(document),
    generateDocumentsMap: generateDocumentsMapV3
  }
]

describe.each(TEST_PARAMS)('Restore Batch task', ({
  version,
  wrapDocument,
  generateDocumentsMap
})=>{
  const config = getBatchedIssueEnvConfig();
  const batchDocuments = new BatchDocuments(config);
  const invalidDocuments = new InvalidDocuments(config);

  beforeEach(async ()=>{
    await clearBucket(config.BATCH_BUCKET_NAME);
    await clearBucket(config.INVALID_BUCKET_NAME);
    jest.setTimeout(1000 * 100);
  }, 1000 * 60);

  describe(version, ()=>{
    test('Restore unwrapped batch, batch.restored=true, batch.composed=true', async ()=>{
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);
      const documentsCount = 10;
      const expectedBatchDocumentsCount = 5;
      const documents = generateDocumentsMap(documentsCount);
      let batchSizeBytes = 0;
      let documentIndex = 0;
      for(let [key, document] of documents){
        await batchDocuments.put({Key: key, Body: JSON.stringify(document)});
        if(documentIndex < expectedBatchDocumentsCount){
          const s3Object = await batchDocuments.get({Key: key});
          batchSizeBytes += s3Object.ContentLength!;
        }
        documentIndex++;
      }


      const batch = new Batch();
      const restoreBatch = new RestoreBatch({
        version,
        wrapped: false,
        batch,
        documentStore,
        invalidDocuments,
        batchDocuments,
        batchTimeSeconds: 60,
        batchSizeBytes,
        attempts: 1,
        attemptsIntervalSeconds: 1
      });

      await restoreBatch.start();

      expect(batch.restored).toBe(true);
      expect(batch.composed).toBe(true);
      expect(batch.wrappedDocuments.size).toBe(0);
      expect(batch.unwrappedDocuments.size).toBe(expectedBatchDocumentsCount);
      for(let [key, document] of batch.unwrappedDocuments){
        const s3Object = await batchDocuments.get({Key: key});
        expect(JSON.parse(s3Object.Body!.toString())).toEqual(document.body);
      }
    })

    test('Restore wrapped batch, batch.restored=true, batch.composed=true', async ()=>{
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);
      const documentsCount = 10;
      const expectedBatchDocumentsCount = 5;
      const documents = generateDocumentsMap(documentsCount);
      let batchSizeBytes = 0;
      let documentIndex = 0;
      for(let [key, document] of documents){
        await batchDocuments.put({Key: key, Body: JSON.stringify(await wrapDocument(document))});
        if(documentIndex < expectedBatchDocumentsCount){
          const s3Object = await batchDocuments.get({Key: key});
          batchSizeBytes += s3Object.ContentLength!;
        }
        documentIndex++;
      }


      const batch = new Batch();
      const restoreBatch = new RestoreBatch({
        version,
        wrapped: true,
        batch,
        documentStore,
        invalidDocuments,
        batchDocuments,
        batchTimeSeconds: 60,
        batchSizeBytes,
        attempts: 1,
        attemptsIntervalSeconds: 1
      });

      await restoreBatch.start();

      expect(batch.restored).toBe(true);
      expect(batch.composed).toBe(true);
      expect(batch.unwrappedDocuments.size).toBe(0);
      expect(batch.wrappedDocuments.size).toBe(expectedBatchDocumentsCount);
      for(let [key, document] of batch.unwrappedDocuments){
        const s3Object = await batchDocuments.get({Key: key});
        expect(JSON.parse(s3Object.Body!.toString())).toEqual(document.body);
      }
    })

    test('Restore unwrapped batch, batch.restored=true, batch.composed=false', async ()=>{
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);
      const documents = generateDocumentsMap(10);
      for(let [key, document] of documents){
        await batchDocuments.put({Key: key, Body: JSON.stringify(document)});
      }


      const batch = new Batch();
      const restoreBatch = new RestoreBatch({
        version,
        wrapped:false,
        batch,
        documentStore,
        invalidDocuments,
        batchDocuments,
        batchTimeSeconds: 60,
        batchSizeBytes: 1024 * 1024 * 1024,
        attempts: 1,
        attemptsIntervalSeconds: 1
      });

      await restoreBatch.start();

      expect(batch.restored).toBe(true);
      expect(batch.composed).toBe(false);
      expect(batch.unwrappedDocuments.size).toBe(documents.size);
      for(let [key, document] of batch.unwrappedDocuments){
        const s3Object = await batchDocuments.get({Key: key});
        expect(JSON.parse(s3Object.Body!.toString())).toEqual(document.body);
      }
    })

    test('Restore wrapped batch, batch.restored=true, batch.composed=false', async ()=>{
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);
      const documents = generateDocumentsMap(10);
      for(let [key, document] of documents){
        await batchDocuments.put({Key: key, Body: JSON.stringify(await wrapDocument(document))});
      }


      const batch = new Batch();
      const restoreBatch = new RestoreBatch({
        version,
        wrapped:true,
        batch,
        documentStore,
        invalidDocuments,
        batchDocuments,
        batchTimeSeconds: 60,
        batchSizeBytes: 1024 * 1024 * 1024,
        attempts: 1,
        attemptsIntervalSeconds: 1
      });

      await restoreBatch.start();

      expect(batch.restored).toBe(true);
      expect(batch.composed).toBe(false);
      expect(batch.unwrappedDocuments.size).toBe(0);
      expect(batch.wrappedDocuments.size).toBe(documents.size);
      for(let [key, document] of batch.wrappedDocuments){
        const s3Object = await batchDocuments.get({Key: key});
        expect(JSON.parse(s3Object.Body!.toString())).toEqual(document.body);
      }
    })

    test('Restore unwrapped batch, batch.restored=false, batch.composed=false', async ()=>{
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);
      const batch = new Batch();
      const restoreBatch = new RestoreBatch({
        version,
        wrapped: false,
        batch,
        documentStore,
        invalidDocuments,
        batchDocuments,
        batchTimeSeconds: 60,
        batchSizeBytes: 1024 * 1024 * 1024,
        attempts: 1,
        attemptsIntervalSeconds: 1
      });

      await restoreBatch.start();

      expect(batch.restored).toBe(false);
      expect(batch.composed).toBe(false);
      expect(batch.unwrappedDocuments.size).toBe(0);
      expect(batch.wrappedDocuments.size).toBe(0);
    })

    test('Restore wrapped batch, batch.restored=false, batch.composed=false', async ()=>{
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);
      const batch = new Batch();
      const restoreBatch = new RestoreBatch({
        version,
        wrapped: true,
        batch,
        documentStore,
        invalidDocuments,
        batchDocuments,
        batchTimeSeconds: 60,
        batchSizeBytes: 1024 * 1024 * 1024,
        attempts: 1,
        attemptsIntervalSeconds: 1
      });

      await restoreBatch.start();

      expect(batch.restored).toBe(false);
      expect(batch.composed).toBe(false);
      expect(batch.unwrappedDocuments.size).toBe(0);
      expect(batch.wrappedDocuments.size).toBe(0);
    })
  })
});
