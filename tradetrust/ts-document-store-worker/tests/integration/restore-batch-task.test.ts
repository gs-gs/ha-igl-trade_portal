import { getBatchedDocumentStoreTaskEnvConfig } from 'src/config';
import { Batch, RestoreBatch } from 'src/tasks';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import {
  BatchDocuments,
  InvalidDocuments
} from 'src/repos';
import {
  clearBucket,
  generateDocumentsMap,
} from 'tests/utils';
import { wrapDocument } from '@govtechsg/open-attestation';


describe('RestoreBatch task integration tests', ()=>{
  jest.setTimeout(1000 * 100);
  const config = getBatchedDocumentStoreTaskEnvConfig();

  beforeEach(async (done)=>{
    await clearBucket(config.BATCH_BUCKET_NAME);
    await clearBucket(config.INVALID_BUCKET_NAME);
    done();
  }, 1000 * 60);

  const batchDocuments = new BatchDocuments(config);
  const invalidDocuments = new InvalidDocuments(config);

  test('restore unwrapped batch, batch.restored=true, batch.composed=true', async ()=>{
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

  test('restore wrapped batch, batch.restored=true, batch.composed=true', async ()=>{
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);
    const documentsCount = 10;
    const expectedBatchDocumentsCount = 5;
    const documents = generateDocumentsMap(documentsCount);
    let batchSizeBytes = 0;
    let documentIndex = 0;
    for(let [key, document] of documents){
      await batchDocuments.put({Key: key, Body: JSON.stringify(wrapDocument(document))});
      if(documentIndex < expectedBatchDocumentsCount){
        const s3Object = await batchDocuments.get({Key: key});
        batchSizeBytes += s3Object.ContentLength!;
      }
      documentIndex++;
    }


    const batch = new Batch();
    const restoreBatch = new RestoreBatch({
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

  test('restore unwrapped batch, batch.restored=true, batch.composed=false', async ()=>{
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);
    const documents = generateDocumentsMap(10);
    for(let [key, document] of documents){
      await batchDocuments.put({Key: key, Body: JSON.stringify(document)});
    }


    const batch = new Batch();
    const restoreBatch = new RestoreBatch({
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

  test('restore wrapped batch, batch.restored=true, batch.composed=false', async ()=>{
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);
    const documents = generateDocumentsMap(10);
    for(let [key, document] of documents){
      await batchDocuments.put({Key: key, Body: JSON.stringify(wrapDocument(document))});
    }


    const batch = new Batch();
    const restoreBatch = new RestoreBatch({
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

  test('restore unwrapped batch, batch.restored=false, batch.composed=false', async ()=>{
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);
    const batch = new Batch();
    const restoreBatch = new RestoreBatch({
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

  test('restore wrapped batch, batch.restored=false, batch.composed=false', async ()=>{
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);
    const batch = new Batch();
    const restoreBatch = new RestoreBatch({
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
});
